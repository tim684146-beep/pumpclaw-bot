import requests
import time
import json
import os
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M = 1000       # Volume minimum 5min en $
MIN_VOLUME_1H = 5000      # Volume minimum 1h en $
MIN_MARKET_CAP = 5000     # Market cap minimum en $
MAX_MARKET_CAP = 10000000    # Market cap maximum en $
CHECK_INTERVAL = 30       # Vérification toutes les 30 secondes
# =============================================

seen_tokens = set()

def get_pumpfun_tokens():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        r = requests.get(url, timeout=10)
        profiles = r.json() if r.status_code == 200 else []
    except:
        profiles = []

    # Récupère les tokens Solana depuis dexscreener
    url2 = "https://api.dexscreener.com/latest/dex/search?q=pump"
    try:
        r2 = requests.get(url2, timeout=10)
        data = r2.json()
        pairs = data.get("pairs", [])
    except:
        pairs = []

    results = []
    for pair in pairs:
        try:
            if pair.get("chainId") != "solana":
                continue

            token_addr = pair.get("baseToken", {}).get("address", "")
            if token_addr in seen_tokens:
                continue

            vol5m = float(pair.get("volume", {}).get("m5", 0) or 0)
            vol1h = float(pair.get("volume", {}).get("h1", 0) or 0)
            mc = float(pair.get("marketCap", 0) or 0)
            price_change_5m = float(pair.get("priceChange", {}).get("m5", 0) or 0)
            price_change_1h = float(pair.get("priceChange", {}).get("h1", 0) or 0)

            if vol5m < MIN_VOLUME_5M:
                continue
            if vol1h < MIN_VOLUME_1H:
                continue
            if mc < MIN_MARKET_CAP or mc > MAX_MARKET_CAP:
                continue

            results.append({
                "name": pair.get("baseToken", {}).get("name", "Unknown"),
                "symbol": pair.get("baseToken", {}).get("symbol", "???"),
                "address": token_addr,
                "price": pair.get("priceUsd", "N/A"),
                "vol5m": vol5m,
                "vol1h": vol1h,
                "mc": mc,
                "change5m": price_change_5m,
                "change1h": price_change_1h,
                "dex": pair.get("dexId", ""),
                "url": pair.get("url", ""),
            })
        except:
            continue

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
    emoji5m = "🟢" if change5m >= 0 else "🔴"
    emoji1h = "🟢" if change1h >= 0 else "🔴"

    mc_formatted = format_number(token["mc"])
    vol5m_formatted = format_number(token["vol5m"])
    vol1h_formatted = format_number(token["vol1h"])

    dex_url = token["url"] or f"https://dexscreener.com/solana/{token['address']}"
    pump_url = f"https://pump.fun/{token['address']}"
    gmgn_url = f"https://gmgn.ai/sol/token/{token['address']}"

    color = 0x00ff88 if change5m >= 0 else 0xff4444

    embed = {
        "username": "🦞 PumpCall BOT",
        "avatar_url": "https://i.imgur.com/wSTFkRM.png",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "💰 Market Cap", "value": mc_formatted, "inline": True},
                {"name": "📊 Vol 5m", "value": vol5m_formatted, "inline": True},
                {"name": "📊 Vol 1h", "value": vol1h_formatted, "inline": True},
                {"name": f"{emoji5m} Change 5m", "value": f"{change5m:+.1f}%", "inline": True},
                {"name": f"{emoji1h} Change 1h", "value": f"{change1h:+.1f}%", "inline": True},
                {"name": "🏦 DEX", "value": token["dex"].upper(), "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener]({dex_url}) • [Pump.fun]({pump_url}) • [GMGN]({gmgn_url})", "inline": False},
                {"name": "📋 CA", "value": f"`{token['address']}`", "inline": False},
            ],
            "footer": {"text": f"PumpCall BOT • {datetime.utcnow().strftime('%H:%M UTC')}"},
            "thumbnail": {"url": "https://i.imgur.com/wSTFkRM.png"}
        }]
    }

    try:
        r = requests.post(https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM, json=embed, timeout=10)
        if r.status_code in [200, 204]:
            print(f"✅ Envoyé: {token['name']} ({token['symbol']})")
            return True
        else:
            print(f"❌ Erreur Discord: {r.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    return False

def main():
    print("🦞 PumpCall BOT démarré !")
    print(f"⚙️ Filtres: Vol5m > {format_number(MIN_VOLUME_5M)} | Vol1h > {format_number(MIN_VOLUME_1H)} | MC {format_number(MIN_MARKET_CAP)}-{format_number(MAX_MARKET_CAP)}")
    print(f"🔄 Vérification toutes les {CHECK_INTERVAL}s\n")

    while True:
        print(f"🔍 Scan en cours... ({datetime.utcnow().strftime('%H:%M:%S')})")
        tokens = get_pumpfun_tokens()
        
        new_count = 0
        for token in tokens:
            if token["address"] not in seen_tokens:
                if send_discord(token):
                    seen_tokens.add(token["address"])
                    new_count += 1
                    time.sleep(1)  # Anti-spam Discord

        print(f"✅ {new_count} nouveaux tokens callés | {len(seen_tokens)} vus au total")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
