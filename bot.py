import requests
import time
import os
from datetime import datetime

# =============================================
# CONFIG
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M   = 25000
MIN_VOLUME_1H   = 60000
MIN_MARKET_CAP  = 1000
MAX_MARKET_CAP  = 3_000_000
MIN_LIQUIDITY   = 30000
MIN_PAIR_AGE_M  = 1
CHECK_INTERVAL  = 60

MAX_BUNDLER_PCT    = 45.0
MAX_INSIDER_PCT    = 25.0
MAX_TOP10_PCT      = 20.0
MAX_RUGCHECK_SCORE = 500

BANNED_FLAGS = [
    "rugpull risk", "honeypot",
    "mint authority enabled", "freeze authority enabled",
    "high holder concentration",
]
# =============================================

REDIS_URL = os.environ.get("REDIS_URL", "")
redis_client = None

def init_redis():
    global redis_client
    if not REDIS_URL:
        print("⚠️ Pas de REDIS_URL — utilisation mémoire locale")
        return
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("✅ Redis connecté !")
    except Exception as e:
        print(f"⚠️ Redis erreur: {e} — utilisation mémoire locale")
        redis_client = None

local_seen = set()

def is_seen(addr):
    if redis_client:
        return redis_client.sismember("seen_tokens", addr)
    return addr in local_seen

def mark_seen(addr):
    if redis_client:
        redis_client.sadd("seen_tokens", addr)
        redis_client.expire("seen_tokens", 60 * 60 * 24 * 7)
    else:
        local_seen.add(addr)


def check_rugcheck(address, symbol="?"):
    try:
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{address}/report", timeout=15)
        if r.status_code == 429:
            return True, "Rate limit"
        if r.status_code != 200:
            return True, f"HTTP {r.status_code}"

        data = r.json()
        score = data.get("score", 0) or 0
        if score > MAX_RUGCHECK_SCORE:
            return False, f"Score trop élevé: {score}"

        for risk in (data.get("risks", []) or []):
            rname = risk.get("name", "").lower()
            for banned in BANNED_FLAGS:
                if banned.lower() in rname:
                    return False, f"Flag: {risk.get('name')}"

        top_holders = data.get("topHolders", []) or []
        if top_holders:
            top10_pct = sum(float(h.get("pct", 0) or 0) for h in top_holders[:10]) * 100
            if top10_pct > MAX_TOP10_PCT:
                return False, f"Top10: {top10_pct:.1f}%"

        bundler_pct = 0.0
        insider_pct = 0.0
        for network in (data.get("insiderNetworks", []) or []):
            n_type = network.get("type", "").lower()
            n_pct  = float(network.get("percentage", 0) or 0)
            if "bundle" in n_type:
                bundler_pct += n_pct
            elif "insider" in n_type or "sniper" in n_type:
                insider_pct += n_pct

        if bundler_pct > MAX_BUNDLER_PCT:
            return False, f"Bundlers: {bundler_pct:.1f}%"
        if insider_pct > MAX_INSIDER_PCT:
            return False, f"Insiders: {insider_pct:.1f}%"

        return True, f"OK (score: {score})"
    except Exception as e:
        return True, f"Erreur: {e}"


def get_all_addresses():
    """Collecte les adresses depuis toutes les sources disponibles."""
    all_addresses = []

    # SOURCE 1 : tokens boostés/profilés sur DexScreener
    for url in [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
        "https://api.dexscreener.com/token-boosts/top/v1",
    ]:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            items = r.json()
            if not isinstance(items, list):
                continue
            for item in items:
                if item.get("chainId") == "solana":
                    addr = item.get("tokenAddress", "")
                    if addr and addr not in all_addresses:
                        all_addresses.append(addr)
        except:
            pass
        time.sleep(1)

    # SOURCE 2 : nouvelles paires Solana (tokens récents)
    try:
        print("🆕 Récupération nouvelles paires Solana...")
        r = requests.get(
            "https://api.dexscreener.com/latest/dex/search?q=solana&rankBy=pairAge&order=asc",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            for pair in data.get("pairs", []):
                if pair.get("chainId") == "solana":
                    addr = (pair.get("baseToken") or {}).get("address", "")
                    if addr and addr not in all_addresses:
                        all_addresses.append(addr)
    except Exception as e:
        print(f"  ⚠️ Nouvelles paires erreur: {e}")
    time.sleep(1)

    # SOURCE 3 : pump.fun nouveaux tokens via API publique
    try:
        print("🔥 Récupération tokens pump.fun récents...")
        r = requests.get(
            "https://frontend-api.pump.fun/coins?offset=0&limit=50&sort=last_trade_timestamp&order=DESC&includeNsfw=false",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            coins = r.json()
            if isinstance(coins, list):
                for coin in coins:
                    addr = coin.get("mint", "")
                    if addr and addr not in all_addresses:
                        all_addresses.append(addr)
                print(f"  ✅ {len(coins)} tokens pump.fun récupérés")
    except Exception as e:
        print(f"  ⚠️ Pump.fun erreur: {e}")
    time.sleep(1)

    print(f"📦 {len(all_addresses)} adresses Solana au total")
    return all_addresses


def process_pairs(all_addresses):
    """Récupère et filtre les données de marché pour chaque adresse."""
    results = []

    for i in range(0, len(all_addresses), 30):
        batch = all_addresses[i:i+30]
        try:
            r = requests.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{('%2C').join(batch)}",
                timeout=10
            )
            if r.status_code != 200:
                continue
            data = r.json()
        except:
            continue

        for pair in data.get("pairs", []):
            try:
                if pair.get("chainId") != "solana":
                    continue
                base = pair.get("baseToken", {}) or {}
                addr = base.get("address", "")
                if not addr or is_seen(addr):
                    continue

                vol5m     = float((pair.get("volume") or {}).get("m5", 0) or 0)
                vol1h     = float((pair.get("volume") or {}).get("h1", 0) or 0)
                mc        = float(pair.get("marketCap", 0) or 0)
                liquidity = float((pair.get("liquidity") or {}).get("usd", 0) or 0)
                change5m  = float((pair.get("priceChange") or {}).get("m5", 0) or 0)
                change1h  = float((pair.get("priceChange") or {}).get("h1", 0) or 0)
                symbol    = base.get("symbol", "?")

                pca = pair.get("pairCreatedAt")
                if pca and (datetime.utcnow().timestamp()*1000 - pca)/60000 < MIN_PAIR_AGE_M:
                    continue
                if vol5m < MIN_VOLUME_5M: continue
                if vol1h < MIN_VOLUME_1H: continue
                if not (MIN_MARKET_CAP <= mc <= MAX_MARKET_CAP): continue
                if liquidity < MIN_LIQUIDITY: continue

                print(f"    🔎 [{symbol}] RugCheck...")
                safe, raison = check_rugcheck(addr, symbol)
                if not safe:
                    print(f"    🚫 [{symbol}] Rejeté — {raison}")
                    mark_seen(addr)
                    continue

                print(f"    ✅ [{symbol}] {raison}")
                mark_seen(addr)
                time.sleep(0.5)

                results.append({
                    "name":     base.get("name", "Unknown"),
                    "symbol":   symbol,
                    "address":  addr,
                    "vol5m":    vol5m,
                    "vol1h":    vol1h,
                    "mc":       mc,
                    "liquidity": liquidity,
                    "change5m": change5m,
                    "change1h": change1h,
                    "url":      f"https://dexscreener.com/solana/{addr}",
                })
            except Exception as e:
                print(f"    ⚠️ {e}")
        time.sleep(1)

    return results


def fmt(n):
    if n is None: return "N/A"
    if n >= 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
    if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if n >= 1_000: return f"${n/1_000:.1f}K"
    return f"${n:.0f}"


def send_discord(token):
    c5, c1 = token["change5m"], token["change1h"]
    color = 0x00ff88 if c5 >= 0 else 0xff4444
    addr = token["address"]
    embed = {
        "username": "🦞 PumpCall BOT",
        "avatar_url": "https://pump.fun/favicon.ico",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "💰 Market Cap",                                 "value": fmt(token["mc"]),        "inline": True},
                {"name": "💧 Liquidité",                                  "value": fmt(token["liquidity"]), "inline": True},
                {"name": "📊 Vol 5m",                                     "value": fmt(token["vol5m"]),     "inline": True},
                {"name": "📊 Vol 1h",                                     "value": fmt(token["vol1h"]),     "inline": True},
                {"name": "🟢 Change 5m" if c5 >= 0 else "🔴 Change 5m", "value": f"{c5:+.1f}%",          "inline": True},
                {"name": "🟢 Change 1h" if c1 >= 0 else "🔴 Change 1h", "value": f"{c1:+.1f}%",          "inline": True},
                {"name": "✅ RugCheck",                                   "value": "Vérifié",               "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener](https://dexscreener.com/solana/{addr}) • [Pump.fun](https://pump.fun/{addr}) • [Axiom](https://axiom.trade/meme/{addr}) • [GMGN](https://gmgn.ai/sol/token/{addr})", "inline": False},
                {"name": "📋 CA", "value": f"`{addr}`", "inline": False},
            ],
            "footer": {"text": f"PumpCall BOT • {datetime.utcnow().strftime('%H:%M UTC')}"},
        }]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in [200, 204]:
            print(f"✅ Callé: {token['name']} | {fmt(token['vol1h'])} vol1h | {fmt(token['mc'])} MC")
            return True
        print(f"❌ Discord {r.status_code}")
    except Exception as e:
        print(f"❌ {e}")
    return False


def main():
    init_redis()
    print("🦞 PumpCall BOT démarré !")
    print(f"🔄 Scan toutes les {CHECK_INTERVAL}s\n")

    while True:
        print(f"\n{'='*50}\n🔍 {datetime.utcnow().strftime('%H:%M:%S UTC')}\n{'='*50}")

        all_addresses = get_all_addresses()
        tokens = process_pairs(all_addresses)

        new_count = 0
        for token in tokens:
            if send_discord(token):
                new_count += 1
                time.sleep(1.5)

        print(f"\n📊 {new_count} callés ce scan")
        print(f"⏳ Prochain scan dans {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
