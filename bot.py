import requests
import time
import json
import os
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M = 500        # Volume minimum 5min en $
MIN_VOLUME_1H = 2500       # Volume minimum 1h en $
MIN_MARKET_CAP = 1000      # Market cap minimum en $
MAX_MARKET_CAP = 50000000  # Market cap maximum en $
CHECK_INTERVAL = 3         # Vérification toutes les 3 secondes
# =============================================

seen_tokens = set()

def get_pumpfun_tokens():
    """Fetch top tokens by volume from DexScreener (public, no auth required) and apply filter criteria."""
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"

    print(f"🌐 API Request → {url}")

    try:
        r = requests.get(url, timeout=10)
        raw_text = r.text
        print(f"📡 HTTP Status: {r.status_code} | Response length: {len(raw_text)} chars")
        print(f"📄 Raw response (first 500 chars): {raw_text[:500]}")
        data = r.json() if r.status_code == 200 else {}
    except Exception as e:
        print(f"⚠️ DexScreener request failed: {e}")
        data = {}

    pairs_raw = data.get("pairs", [])
    print(f"🔢 Pairs returned from API: {len(pairs_raw)}")

    results = []
    for pair in pairs_raw:
        try:
            # Only process Solana pairs
            if pair.get("chainId", "") != "solana":
                continue

            base_token = pair.get("baseToken", {}) or {}
            token_addr = base_token.get("address", "")
            if not token_addr or token_addr in seen_tokens:
                continue

            # DexScreener volume fields are nested under "volume": {"m5": ..., "h1": ...}
            volume = pair.get("volume", {}) or {}
            vol5m = float(volume.get("m5", 0) or 0)
            vol1h = float(volume.get("h1", 0) or 0)
            mc    = float(pair.get("marketCap", 0) or 0)

            # Price changes are nested under "priceChange": {"m5": ..., "h1": ...}
            price_change = pair.get("priceChange", {}) or {}
            price_change_5m = float(price_change.get("m5", 0) or 0)
            price_change_1h = float(price_change.get("h1", 0) or 0)

            symbol = base_token.get("symbol", "?")

            if vol5m < MIN_VOLUME_5M:
                print(f"  ⏭️  [{symbol}] Skipped — vol5m ${vol5m:.2f} < ${MIN_VOLUME_5M}")
                continue
            if vol1h < MIN_VOLUME_1H:
                print(f"  ⏭️  [{symbol}] Skipped — vol1h ${vol1h:.2f} < ${MIN_VOLUME_1H}")
                continue
            if mc < MIN_MARKET_CAP or mc > MAX_MARKET_CAP:
                print(f"  ⏭️  [{symbol}] Skipped — mc ${mc:.2f} out of range [${MIN_MARKET_CAP}, ${MAX_MARKET_CAP}]")
                continue

            price = pair.get("priceUsd", "N/A")

            results.append({
                "name":    base_token.get("name", "Unknown"),
                "symbol":  symbol,
                "address": token_addr,
                "price":   str(price) if price != "N/A" else "N/A",
                "vol5m":   vol5m,
                "vol1h":   vol1h,
                "mc":      mc,
                "change5m": price_change_5m,
                "change1h": price_change_1h,
                "dex":     "dexscreener",
                "url":     f"https://dexscreener.com/solana/{token_addr}",
            })
        except Exception:
            continue

    print(f"✅ Tokens passing all filters: {len(results)}")
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

    dexscreener_url = token["url"] or f"https://dexscreener.com/solana/{token['address']}"
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
                {"name": "📡 Source", "value": "DexScreener", "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener]({dexscreener_url}) • [Pump.fun]({pump_url}) • [GMGN]({gmgn_url})", "inline": False},
                {"name": "📋 CA", "value": f"`{token['address']}`", "inline": False},
            ],
            "footer": {"text": f"PumpCall BOT • {datetime.utcnow().strftime('%H:%M UTC')}"},
            "thumbnail": {"url": "https://i.imgur.com/wSTFkRM.png"}
        }]
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
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
