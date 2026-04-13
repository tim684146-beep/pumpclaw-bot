import requests
import time
from datetime import datetime

# =============================================
# CONFIG - À MODIFIER
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
MIN_VOLUME_5M   = 500        # Volume minimum 5min en $
MIN_VOLUME_1H   = 2500       # Volume minimum 1h en $
MIN_MARKET_CAP  = 1000       # Market cap minimum en $
MAX_MARKET_CAP  = 50_000_000 # Market cap maximum en $
MIN_LIQUIDITY   = 5000       # Liquidité minimum en $
MIN_PAIR_AGE_M  = 10         # Age minimum de la paire en minutes
CHECK_INTERVAL  = 60         # Scan toutes les 60 secondes
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
