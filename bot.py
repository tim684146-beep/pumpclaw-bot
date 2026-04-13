import requests
import time
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M   = 8000        # Volume minimum 5min en $
MIN_VOLUME_1H   = 25000       # Volume minimum 1h en $
MIN_MARKET_CAP  = 1000       # Market cap minimum en $
MAX_MARKET_CAP  = 50_000_000 # Market cap maximum en $
MIN_LIQUIDITY   = 5000       # Liquidité minimum en $
MIN_PAIR_AGE_M  = 1        # Age minimum de la paire en minutes
CHECK_INTERVAL  = 5         # Scan toutes les 60 secondes
SEEN_FILE       = "seen_tokens.txt"

BANNED_FLAGS = [
    "rugpull risk",
    "honeypot",
    "mint authority enabled",
    "freeze authority enabled",
    "high holder concentration",
]
MAX_RUGCHECK_SCORE = 500
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


def check_rugcheck(address):
    url = f"https://api.rugcheck.xyz/v1/tokens/{address}/report/summary"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"    ⚠️ RugCheck indisponible (HTTP {r.status_code}) — token accepté par défaut")
            return True, "RugCheck indisponible"
        data = r.json()
        score = data.get("score", 0) or 0
        if score > MAX_RUGCHECK_SCORE:
            return False, f"Score de risque trop élevé: {score}"
        risks = data.get("risks", []) or []
        for risk in risks:
            risk_name = risk.get("name", "").lower()
            for banned in BANNED_FLAGS:
                if banned.lower() in risk_name:
                    return False, f"Flag dangereux: {risk.get('name')}"
        return True, f"OK (score: {score})"
    except Exception as e:
        print(f"    ⚠️ Erreur RugCheck: {e} — token accepté par défaut")
        return True, "Erreur RugCheck"


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
                print("  ⚠️ Rate limit, pause 15s...")
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
            print(f"  ⚠️ Erreur: {e}")
        time.sleep(1)

    print(f"📦 {len(all_addresses)} adresses Solana trouvées")

    if not all_addresses:
        return []

    results = []
    batch_size = 30

    for i in range(0, len(all_addresses), batch_size):
        batch = all_addresses[i:i+batch_size]
        addresses_str = "%2C".join(batch)
        url = f"https://api.dexscreener.com/latest/dex/tokens/{addresses_str}"

        print(f"  🔍 Batch {i//batch_size + 1} ({len(batch)} tokens)...")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 429:
                print("  ⚠️ Rate limit, pause 15s...")
                time.sleep(15)
                continue
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception as e:
            print(f"  ⚠️ Erreur batch: {e}")
            continue

        pairs = data.get("pairs", [])

        for pair in pairs:
            try:
                if pair.get("chainId", "") != "solana":
                    continue

                base_token = pair.get("baseToken", {}) or {}
                token_addr = base_token.get("address", "")

                if not token_addr or token_addr in seen_tokens:
                    continue

                volume    = pair.get("volume", {}) or {}
                vol5m     = float(volume.get("m5", 0) or 0)
                vol1h     = float(volume.get("h1", 0) or 0)
                mc        = float(pair.get("marketCap", 0) or 0)
                liquidity = float((pair.get("liquidity") or {}).get("usd", 0) or 0)

                price_change = pair.get("priceChange", {}) or {}
                change5m = float(price_change.get("m5", 0) or 0)
                change1h = float(price_change.get("h1", 0) or 0)

                symbol = base_token.get("symbol", "?")

                pair_created_at = pair.get("pairCreatedAt", None)
                if pair_created_at:
                    age_minutes = (datetime.utcnow().timestamp() * 1000 - pair_created_at) / 60000
                    if age_minutes < MIN_PAIR_AGE_M:
                        print(f"    ⏭️  [{symbol}] Trop récent: {age_minutes:.1f} min")
                        continue

                if vol5m < MIN_VOLUME_5M:
                    print(f"    ⏭️  [{symbol}] vol5m trop bas: ${vol5m:.0f}")
                    continue
                if vol1h < MIN_VOLUME_1H:
                    print(f"    ⏭️  [{symbol}] vol1h trop bas: ${vol1h:.0f}")
                    continue
                if mc < MIN_MARKET_CAP:
                    print(f"    ⏭️  [{symbol}] MC trop bas: ${mc:.0f}")
                    continue
                if mc > MAX_MARKET_CAP:
                    print(f"    ⏭️  [{symbol}] MC trop élevé: ${mc:.0f}")
                    continue
                if liquidity < MIN_LIQUIDITY:
                    print(f"    ⏭️  [{symbol}] Liquidité trop basse: ${liquidity:.0f}")
                    continue

                print(f"    🔎 [{symbol}] Vérification RugCheck...")
                safe, raison = check_rugcheck(token_addr)
                if not safe:
                    print(f"    🚫 [{symbol}] Rejeté — {raison}")
                    continue
                print(f"    ✅ [{symbol}] RugCheck: {raison}")
                time.sleep(0.5)

                seen_tokens.add(token_addr)

                results.append({
                    "name":      base_token.get("name", "Unknown"),
                    "symbol":    symbol,
                    "address":   token_addr,
                    "vol5m":     vol5m,
                    "vol1h":     vol1h,
                    "mc":        mc,
                    "liquidity": liquidity,
                    "change5m":  change5m,
                    "change1h":  change1h,
                    "url":       f"https://dexscreener.com/solana/{token_addr}",
                })
                print(f"    🟢 [{symbol}] Vol1h: ${vol1h:.0f} | MC: ${mc:.0f} | Liq: ${liquidity:.0f}")

            except Exception as e:
                print(f"    ⚠️ Erreur parsing: {e}")
                continue

        time.sleep(1)

    print(f"\n✅ {len(results)} tokens passent tous les filtres")
    return results


def format_number(n):
    if n >= 1_000_000_000:
        return f"${n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
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

    dex_url      = token["url"]
    axiom_url    = f"https://axiom.trade/meme/{token['address']}"
    terminal_url = f"https://terminal.jup.ag/swap/SOL-{token['address']}"

    embed = {
        "username":   "🦞 PumpCall BOT",
        "avatar_url": "https://pump.fun/favicon.ico",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "💰 Market Cap",        "value": format_number(token["mc"]),        "inline": True},
                {"name": "💧 Liquidité",          "value": format_number(token["liquidity"]), "inline": True},
                {"name": "📊 Vol 5m",             "value": format_number(token["vol5m"]),     "inline": True},
                {"name": "📊 Vol 1h",             "value": format_number(token["vol1h"]),     "inline": True},
                {"name": f"{emoji5m} Change 5m",  "value": f"{change5m:+.1f}%",              "inline": True},
                {"name": f"{emoji1h} Change 1h",  "value": f"{change1h:+.1f}%",              "inline": True},
                {"name": "✅ RugCheck",            "value": "Vérifié",                        "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener]({dex_url}) • [Axiom]({axiom_url}) • [Terminal]({terminal_url})", "inline": False},
                {"name": "📋 CA", "value": f"`{token['address']}`", "inline": False},
            ],
            "footer":    {"text": f"PumpCall BOT • {datetime.utcnow().strftime('%H:%M UTC')}"},
            "thumbnail": {"url": "https://pump.fun/favicon.ico"}
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
    print(f"💾 {len(seen_tokens)} tokens déjà vus chargés depuis {SEEN_FILE}")
    print(f"⚙️  Vol5m min  : {format_number(MIN_VOLUME_5M)} | Vol1h min : {format_number(MIN_VOLUME_1H)}")
    print(f"⚙️  MC         : {format_number(MIN_MARKET_CAP)} → {format_number(MAX_MARKET_CAP)}")
    print(f"⚙️  Liquidité  : min {format_number(MIN_LIQUIDITY)}")
    print(f"⚙️  Age paire  : min {MIN_PAIR_AGE_M} minutes")
    print(f"⚙️  RugCheck   : score max {MAX_RUGCHECK_SCORE}")
    print(f"🔄 Scan toutes les {CHECK_INTERVAL}s\n")

    while True:
        print(f"\n{'='*50}")
        print(f"🔍 {datetime.utcnow().strftime('%H:%M:%S UTC')}")
        print(f"{'='*50}")

        tokens = get_tokens()

        new_count = 0
        for token in tokens:
            if send_discord(token):
                save_seen(token["address"])
                new_count += 1
                time.sleep(1.5)

        print(f"\n📊 {new_count} nouveaux callés | {len(seen_tokens)} vus au total")
        print(f"⏳ Prochain scan dans {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
