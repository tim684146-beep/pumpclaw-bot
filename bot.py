import requests
import time
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M   = 8000
MIN_VOLUME_1H   = 25000
MIN_MARKET_CAP  = 1000
MAX_MARKET_CAP  = 50_000_000
MIN_LIQUIDITY   = 5000
MIN_PAIR_AGE_M  = 1
CHECK_INTERVAL  = 5
SEEN_FILE       = "seen_tokens.txt"

# =============================================
# FILTRES ANTI-SCAM
# =============================================
MAX_BUNDLER_PCT    = 45.0   # Max % supply par bundlers
MAX_INSIDER_PCT    = 25.0   # Max % supply par insiders
MAX_TOP10_PCT      = 20.0   # Max % supply top 10 holders
MAX_RUGCHECK_SCORE = 500

BANNED_FLAGS = [
    "rugpull risk",
    "honeypot",
    "mint authority enabled",
    "freeze authority enabled",
    "high holder concentration",
]
# =============================================

def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def save_seen(addr):
    with open(SEEN_FILE, "a") as f:
        f.write(addr + "\n")

seen_tokens = load_seen()


def check_rugcheck(address, symbol="?"):
    stats = {"bundler_pct": None, "insider_pct": None, "top10_pct": None, "score": None}
    url = f"https://api.rugcheck.xyz/v1/tokens/{address}/report"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 429:
            print(f"    ⚠️ RugCheck rate limit — accepté par défaut")
            return True, "Rate limit", stats
        if r.status_code != 200:
            print(f"    ⚠️ RugCheck HTTP {r.status_code} — accepté par défaut")
            return True, f"HTTP {r.status_code}", stats

        data = r.json()

        # Score global
        score = data.get("score", 0) or 0
        stats["score"] = score
        if score > MAX_RUGCHECK_SCORE:
            return False, f"Score trop élevé: {score}", stats

        # Flags dangereux
        for risk in (data.get("risks", []) or []):
            rname = risk.get("name", "").lower()
            for banned in BANNED_FLAGS:
                if banned.lower() in rname:
                    return False, f"Flag: {risk.get('name')}", stats

        # Top 10 holders
        top_holders = data.get("topHolders", []) or []
        if top_holders:
            top10_pct = sum(float(h.get("pct", 0) or 0) for h in top_holders[:10]) * 100
            stats["top10_pct"] = top10_pct
            if top10_pct > MAX_TOP10_PCT:
                return False, f"Top10 holders: {top10_pct:.1f}% > {MAX_TOP10_PCT}%", stats

        # Bundlers & Insiders via insiderNetworks
        bundler_pct = 0.0
        insider_pct = 0.0
        for network in (data.get("insiderNetworks", []) or []):
            n_type = network.get("type", "").lower()
            n_pct  = float(network.get("percentage", 0) or 0)
            if "bundle" in n_type or "bundler" in n_type:
                bundler_pct += n_pct
            elif "insider" in n_type or "sniper" in n_type:
                insider_pct += n_pct

        stats["bundler_pct"] = bundler_pct
        stats["insider_pct"] = insider_pct

        if bundler_pct > MAX_BUNDLER_PCT:
            return False, f"Bundlers: {bundler_pct:.1f}% > {MAX_BUNDLER_PCT}%", stats
        if insider_pct > MAX_INSIDER_PCT:
            return False, f"Insiders: {insider_pct:.1f}% > {MAX_INSIDER_PCT}%", stats

        return True, f"OK (score: {score})", stats

    except Exception as e:
        print(f"    ⚠️ Erreur RugCheck: {e} — accepté par défaut")
        return True, f"Erreur: {e}", stats


def get_tokens():
    all_addresses = []
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/token-boosts/latest/v1",
        "https://api.dexscreener.com/token-boosts/top/v1",
    ]
    for url in endpoints:
        print(f"🌐 {url}")
        try:
            r = requests.get(url, timeout=10)
            print(f"  📡 HTTP {r.status_code}")
            if r.status_code == 429:
                time.sleep(15)
                continue
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
        except Exception as e:
            print(f"  ⚠️ {e}")
        time.sleep(1)

    print(f"📦 {len(all_addresses)} adresses Solana trouvées")
    if not all_addresses:
        return []

    results = []
    for i in range(0, len(all_addresses), 30):
        batch = all_addresses[i:i+30]
        url = f"https://api.dexscreener.com/latest/dex/tokens/{('%2C').join(batch)}"
        print(f"  🔍 Batch {i//30 + 1} ({len(batch)} tokens)...")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 429:
                time.sleep(15)
                continue
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception as e:
            print(f"  ⚠️ {e}")
            continue

        for pair in data.get("pairs", []):
            try:
                if pair.get("chainId") != "solana":
                    continue
                base = pair.get("baseToken", {}) or {}
                addr = base.get("address", "")
                if not addr or addr in seen_tokens:
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
                if vol5m < MIN_VOLUME_5M:
                    continue
                if vol1h < MIN_VOLUME_1H:
                    continue
                if not (MIN_MARKET_CAP <= mc <= MAX_MARKET_CAP):
                    continue
                if liquidity < MIN_LIQUIDITY:
                    continue

                print(f"    🔎 [{symbol}] RugCheck...")
                safe, raison, rc = check_rugcheck(addr, symbol)
                if not safe:
                    print(f"    🚫 [{symbol}] Rejeté — {raison}")
                    seen_tokens.add(addr)
                    continue
                print(f"    ✅ [{symbol}] {raison} | Top10: {rc['top10_pct']}% | Bundlers: {rc['bundler_pct']}% | Insiders: {rc['insider_pct']}%")
                time.sleep(0.5)

                seen_tokens.add(addr)
                results.append({
                    "name": base.get("name", "Unknown"), "symbol": symbol,
                    "address": addr, "vol5m": vol5m, "vol1h": vol1h,
                    "mc": mc, "liquidity": liquidity, "change5m": change5m, "change1h": change1h,
                    "url": f"https://dexscreener.com/solana/{addr}",
                    "rc_score": rc.get("score"), "bundler_pct": rc.get("bundler_pct"),
                    "insider_pct": rc.get("insider_pct"), "top10_pct": rc.get("top10_pct"),
                })
            except Exception as e:
                print(f"    ⚠️ {e}")
        time.sleep(1)

    print(f"\n✅ {len(results)} tokens passent les filtres")
    return results


def fmt(n):
    if n is None: return "N/A"
    if n >= 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
    if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if n >= 1_000: return f"${n/1_000:.1f}K"
    return f"${n:.0f}"

def pct(v):
    return f"{v:.1f}%" if v is not None else "N/A"


def send_discord(token):
    c5 = token["change5m"]
    c1 = token["change1h"]
    color = 0x00ff88 if c5 >= 0 else 0xff4444
    e5 = "🟢" if c5 >= 0 else "🔴"
    e1 = "🟢" if c1 >= 0 else "🔴"

    addr = token["address"]
    embed = {
        "username": "🦞 PumpCall BOT",
        "avatar_url": "https://pump.fun/favicon.ico",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "💰 Market Cap",       "value": fmt(token["mc"]),        "inline": True},
                {"name": "💧 Liquidité",         "value": fmt(token["liquidity"]), "inline": True},
                {"name": "📊 Vol 5m",            "value": fmt(token["vol5m"]),     "inline": True},
                {"name": "📊 Vol 1h",            "value": fmt(token["vol1h"]),     "inline": True},
                {"name": f"{e5} Change 5m",      "value": f"{c5:+.1f}%",          "inline": True},
                {"name": f"{e1} Change 1h",      "value": f"{c1:+.1f}%",          "inline": True},
                {"name": "🤖 Bundlers",          "value": pct(token["bundler_pct"]), "inline": True},
                {"name": "🕵️ Insiders",         "value": pct(token["insider_pct"]), "inline": True},
                {"name": "🐳 Top 10 Holders",   "value": pct(token["top10_pct"]),   "inline": True},
                {"name": "✅ RugCheck Score",    "value": str(token.get("rc_score", "N/A")), "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener](https://dexscreener.com/solana/{addr}) • [Pump.fun](https://pump.fun/{addr}) • [Axiom](https://axiom.trade/meme/{addr}) • [GMGN](https://gmgn.ai/sol/token/{addr})", "inline": False},
                {"name": "📋 CA", "value": f"`{addr}`", "inline": False},
            ],
            "footer": {"text": f"Bundlers <{MAX_BUNDLER_PCT}% • Insiders <{MAX_INSIDER_PCT}% • Top10 <{MAX_TOP10_PCT}% • {datetime.utcnow().strftime('%H:%M UTC')}"},
            "thumbnail": {"url": "https://pump.fun/favicon.ico"}
        }]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in [200, 204]:
            print(f"✅ Callé: {token['name']} | Vol1h: {fmt(token['vol1h'])} | MC: {fmt(token['mc'])}")
            return True
        print(f"❌ Discord {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"❌ {e}")
    return False


def main():
    print("🦞 PumpCall BOT démarré !")
    print(f"🛡️  Filtres anti-scam: Bundlers <{MAX_BUNDLER_PCT}% | Insiders <{MAX_INSIDER_PCT}% | Top10 <{MAX_TOP10_PCT}%")
    print(f"⚙️  Vol5m >{fmt(MIN_VOLUME_5M)} | Vol1h >{fmt(MIN_VOLUME_1H)} | MC {fmt(MIN_MARKET_CAP)}→{fmt(MAX_MARKET_CAP)}")
    print(f"🔄 Scan toutes les {CHECK_INTERVAL}s\n")

    while True:
        print(f"\n{'='*50}\n🔍 {datetime.utcnow().strftime('%H:%M:%S UTC')}\n{'='*50}")
        tokens = get_tokens()
        new_count = 0
        for token in tokens:
            if send_discord(token):
                save_seen(token["address"])
                new_count += 1
                time.sleep(1.5)
        print(f"\n📊 {new_count} callés | {len(seen_tokens)} vus au total")
        print(f"⏳ Prochain scan dans {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
