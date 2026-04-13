import requests
import time
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M  = 5000        # Volume minimum 5min en $
MIN_VOLUME_1H  = 2500       # Volume minimum 1h en $
MIN_MARKET_CAP = 1000       # Market cap minimum en $
MAX_MARKET_CAP = 50_000_000 # Market cap maximum en $
CHECK_INTERVAL = 5         # Scan toutes les 5 secondes
# =============================================

seen_tokens = set()

def get_trending_solana_tokens():
    url = "https://api.dexscreener.com/latest/dex/search?q=SOL&rankBy=volume&order=desc"
    
    print(f"🌐 Requête trending Solana...")
    try:
        r = requests.get(url, timeout=10)
        print(f"📡 HTTP {r.status_code} | {len(r.text)} chars")
        if r.status_code == 429:
            print("⚠️ Rate limit, pause 15s...")
            time.sleep(15)
            return []
        if r.status_code != 200:
            print(f"❌ Erreur API: {r.status_code}")
            return []
        data = r.json()
    except Exception as e:
        print(f"⚠️ Erreur requête: {e}")
        return []

    pairs = data.get("pairs", [])
    print(f"📦 {len(pairs)} paires reçues")

    # Trier par volume 1h décroissant
    pairs.sort(key=lambda p: float((p.get("volume") or {}).get("h1") or 0), reverse=True)

    results = []
    for pair in pairs:
        try:
            # Solana uniquement
            if pair.get("chainId", "") != "solana":
                continue

            base_token = pair.get("baseToken", {}) or {}
            token_addr = base_token.get("address", "")
            if not token_addr or token_addr in seen_tokens:
                continue

            volume   = pair.get("volume", {}) or {}
            vol5m    = float(volume.get("m5", 0) or 0)
            vol1h    = float(volume.get("h1", 0) or 0)
            mc       = float(pair.get("marketCap", 0) or 0)

            price_change = pair.get("priceChange", {}) or {}
            change5m = float(price_change.get("m5", 0) or 0)
            change1h = float(price_change.get("h1", 0) or 0)

            symbol = base_token.get("symbol", "?")

            # Filtres volume & market cap
            if vol5m < MIN_VOLUME_5M:
                print(f"  ⏭️  [{symbol}] vol5m trop bas: ${vol5m:.0f}")
                continue
            if vol1h < MIN_VOLUME_1H:
                print(f"  ⏭️  [{symbol}] vol1h trop bas: ${vol1h:.0f}")
                continue
            if mc < MIN_MARKET_CAP:
                print(f"  ⏭️  [{symbol}] MC trop bas: ${mc:.0f}")
                continue
            if mc > MAX_MARKET_CAP:
                print(f"  ⏭️  [{symbol}] MC trop élevé: ${mc:.0f}")
                continue

            results.append({
                "name":     base_token.get("name", "Unknown"),
                "symbol":   symbol,
                "address":  token_addr,
                "price":    str(pair.get("priceUsd", "N/A")),
                "vol5m":    vol5m,
                "vol1h":    vol1h,
                "mc":       mc,
                "change5m": change5m,
                "change1h": change1h,
                "url":      f"https://dexscreener.com/solana/{token_addr}",
            })

        except Exception as e:
            print(f"⚠️ Erreur parsing: {e}")
            continue

    print(f"✅ {len(results)} tokens passent les filtres")
    return results


def format_number(n):
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"${n/1_000:.1f}K"
    return f"${n:.0f}"


def send_discord(token):
    change5m = token["change5m"]
    change1h = token["change1h"]
    emoji5m  = "🟢" if change5m >= 0 else "🔴"
    emoji1h  = "🟢" if change1h >= 0 else "🔴"
    color    = 0x00ff88 if change5m >= 0 else 0xff4444

    dex_url  = token["url"]
    pump_url = f"https://pump.fun/{token['address']}"
    gmgn_url = f"https://gmgn.ai/sol/token/{token['address']}"

    embed = {
        "username":   "🦞 PumpCall BOT",
        "avatar_url": "https://i.imgur.com/wSTFkRM.png",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "💰 Market Cap",       "value": format_number(token["mc"]),    "inline": True},
                {"name": "📊 Vol 5m",            "value": format_number(token["vol5m"]), "inline": True},
                {"name": "📊 Vol 1h",            "value": format_number(token["vol1h"]), "inline": True},
                {"name": f"{emoji5m} Change 5m", "value": f"{change5m:+.1f}%",          "inline": True},
                {"name": f"{emoji1h} Change 1h", "value": f"{change1h:+.1f}%",          "inline": True},
                {"name": "💵 Prix",              "value": f"${token['price']}",          "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener]({dex_url}) • [Pump.fun]({pump_url}) • [GMGN]({gmgn_url})", "inline": False},
                {"name": "📋 CA", "value": f"`{token['address']}`", "inline": False},
            ],
            "footer":    {"text": f"PumpCall BOT • {datetime.utcnow().strftime('%H:%M UTC')}"},
            "thumbnail": {"url": "https://i.imgur.com/wSTFkRM.png"}
        }]
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in [200, 204]:
            print(f"✅ Callé: {token['name']} (${token['symbol']}) | Vol1h: {format_number(token['vol1h'])} | MC: {format_number(token['mc'])}")
            return True
        else:
            print(f"❌ Discord erreur {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")
    return False


def main():
    print("🦞 PumpCall BOT démarré !")
    print(f"⚙️  Vol5m min: {format_number(MIN_VOLUME_5M)} | Vol1h min: {format_number(MIN_VOLUME_1H)}")
    print(f"⚙️  MC: {format_number(MIN_MARKET_CAP)} → {format_number(MAX_MARKET_CAP)}")
    print(f"🔄 Scan toutes les {CHECK_INTERVAL}s\n")

    while True:
        print(f"\n{'='*50}")
        print(f"🔍 {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        print(f"{'='*50}")

        tokens = get_trending_solana_tokens()

        new_count = 0
        for token in tokens:
            if token["address"] not in seen_tokens:
                if send_discord(token):
                    seen_tokens.add(token["address"])
                    new_count += 1
                    time.sleep(1.5)  # anti-spam Discord

        print(f"📊 {new_count} nouveaux callés | {len(seen_tokens)} vus au total")
        print(f"⏳ Prochain scan dans {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
