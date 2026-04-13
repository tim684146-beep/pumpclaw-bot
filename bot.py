import requests
import time
import os
from datetime import datetime

# =============================================
# CONFIG
# =============================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1493001312449593364/nBZ2Wu2ljp0o-FY9Twfui2ykn2y-4ub8JQDgZoFU7jk5leoYQpD-015XDWUnFlM05NGM"
HELIUS_API_KEY      = "f389b283-e569-484d-a5ad-bc335464f952"
HELIUS_RPC_URL      = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

DEV_WALLETS = [
    "25atNEyHwGiBgeUGDMiftBgKNDeShuKxaTSJLo5yCSSu",
    "HDKmYwf7AHqtyatnfcCYony7TziEuNQPAGA7VH36SQVu",
    "AB5EUPJjBSAoGqWCAQ3EHPSTbBarsAMEf6TJi7tibo2D",
    "4sDokeqQ9mJZSgCo5eHcZZxCAY2aZAZJcYwtsiky7gQD",
    "8PPHLbTjvBNvzbWFWosoAsu58dsRN7hpgGDVNXwZw2q2",
    "EYfdt8cNFyyTEJKp18dcoVbgUHDnM1SK3bT2uKj9XXHc",
    "5TcyQLh8ojBf81DKeRC4vocTbNKJpJCsR9Kei16kLqDM",
    "5cREtdfeZPT65xD3HMiJCBKJea9SBHZNREjXHG48Tv9y",
    "DGPWxJTrfw4WM9WsnyFCDQGsAfYfjDagrBNRnBNnPW3m",
    "72x3Eo99X44zweqUZNFJh9NzXPL462dxK1WbiE8ZJ8CS",
    "GZVSEAajExLJEvACHHQcujBw7nJq98GWUEZtood9LM9b",
    "BxMLRRVA1gbkTKKGt5hXLFBjUhETgkunvKkfAPEDtPnZ",
    "B8WicPqBgrGmAa8QMQgdJCFFFAAaPbSxzLUG9dW6WstF",
    "5f8dDi7o8tGYkFVALB6VixhStULNDxxqNivgWEfr2z17",
    "Fyv2htM47t4BRiRLUXNf1QYvUirREy7WDRn73E41J2h5",
    "AxmFqz3pbhj6HDK9dC1u7LsYP3rbsTJyKkeCMSpAxrgU",
    "CtPxvpWo1pk7HtL6KwpCLMMdsXHC6fdqAN1bPiracaQq",
    "GwbgS6C5F2fhm9uSb9G79QAyUi3ApLAyftoo4KkACqkZ",
    "MNhBbrscBPmeid54buiqSgyWa4D8PY6uKHoK2wJsTJN",
    "DdZG8dw12CsHjj2Ytfo1vKNPPoU4DEYSMSxdhPjo5U6N",
    "89VB5UmvopuCFmp5Mf8YPX28fGvvqn79afCgouQuPyhY",
    "HyYNVYmnFmi87NsQqWzLJhUTPBKQUfgfhdbBa554nMFF",
    "7E9jfxCczubz4FXkkVKzUMHXGwzJxyppC4m7y3ew8ATg",
    "4qMhJ42sCexUkXgqEkPt9nsyK93d92QeNGKZNyNYPGUb",
    "Cj3ScshvGDLKtMqxGd5rb8npSM5zq6ig5GY6UuJgCFRU",
    "EdDP5KrpqHwdggghoQuzJMVwegkA6gwspTa1JJPL6m13",
    "2ptGoNPbDA7TgJP3LemJXrShSkFsjWsaDANnjsdEunmg",
    "E4WuDtSt39GpUacPoFnaqU1jSni8LMG3nGt2mWL331NA",
    "7YeCaAqhzhtRio1mddqaQzhvWRWXEsm4GSyfm4VwDsvL",
    "9AzvaMJnG7vJ98nGbxh9V7pE3tSQsh6cvy8rc21D3yX1",
    "FRZz1xLeEz5DjqynK1efNw9u2DcvWYc6sPPy2zTDLXBH",
    "7bo6edP4nNawuaNLk8CP8P8Uz4Csv4xWLweLSiAsa2cV",
    "7VzKD7nTQg9ypcJtT1cA34aa9wLGRHzjGvZNQx53r8WA",
    "6uNm1NxNgURuuPMynWcfTPjJJXV3g6bPgJTF43hEVdcX",
    "HZ31eb27ix1AZ6dqQTQ6iJdPayn6HP4GR25hhWy8Pidz",
    "9gw1QyjcFzmuMTn5FQv6UJ5m8yz7oTqy97gYLUg7LER6",
    "bwamJzztZsepfkteWRChggmXuiiCQvpLqPietdNfSXa",
    "8YcbyX92UHTU23HZv3ccP9o13qibErQkKaUjoxqxd7SJ",
    "4fZFcK8ms3bFMpo1ACzEUz8bH741fQW4zhAMGd5yZMHu",
    "FNVwcZieXbmhfNjzQWyiGzxxPVgyBVPqPx55m7qz2Ko6",
    "2weHfKKnfv85Tq31k2Dq5A5YhkaDvujS8oTZLMvdSNzc",
    "J3k4T9XHhhAGrZ64ukcya19FApC8jf8xaTWwYJfjTR4p",
    "pyPAunk5JiHjjQfeh19mqfMAFhK4ybXhkEQbeKGpump",
    "9zPxrXcor3gzTsg73LGBji6VVpfNYeiAq9T9GDPmKTHV",
    "4DrtsW86GarGJJeYrBwYCjoyMgDPG95QWSGhFHvCkU2s",
    "F4HGHWyaCvDkUF88svvCHhSMpR9YzHCYSNmojaKQtRSB",
    "CkjEpxsd4Lz1mftFMwuYsdd1MjFXYmmakQzaSvguTu5G",
    "5DDEaV8fD1d5Ygn7P2Naq1WzWJAULa5TX2GBJxicZM9g",
    "DTQQf6xhbRFqbSUzHsQ4e1PJroCR3dVKvUnt7sj11HJc",
    "DjM7Tu7whh6P3pGVBfDzwXAx2zaw51GJWrJE3PwtuN7s",
    "3pN9Xs3ZUQDKyXHxvs7WYHW2NXph3h5BR7JfUDVebGCg",
    "ArfVe1K5gt5zsxzRCWSQeWc1rJSJjZzuuYxmvRh71mMQ",
    "78N177fzNJpp8pG49xDv1efYcTMSzo9tPTKEA9mAVkh2",
    "3tc4BVAdzjr1JpeZu6NAjLHyp4kK3iic7TexMBYGJ4Xk",
    "6P2XrFUBfm6qGSadmopSMovtqNDN5hWj3JJ3bqjaL2NP",
    "CfkaAru9ArJ2tAStYHvbAyRBJL3EhDzsWYV2KYg9shxB",
    "8mk2xuJoiZ3abZBE3o1EuTUtQ7MszgjhNbu3EzxKuw86",
    "FbMxP3GVq8TQ36nbYgx4NP9iygMpwAwFWJwW81ioCiSF",
    "36DWP52MVRDooYNrcRVDyoCh2R1fPXCYqKJQYg9pFQoE",
    "JBuMJY4w37nYvBhrngjbitSdciamg98N9Vt26NWusuXd",
    "BT2sdwJeDWqXNUNBJwtKWBD7RjquACfjo1rT9vpZLUSA",
    "5ZJQSU7YHuDQqtUhL1z65UUuEnaJJ73J3YCBAo9uuTVD",
    "2RH6rUTPBJ9rUDPpuV9b8z1YL56k1tYU6Uk5ZoaEFFSK",
    "CyaE1VxvBrahnPWkqm5VsdCvyS2QmNht2UFrKJHga54o",
    "5sNnKuWKUtZkdC1eFNyqz3XHpNoCRQ1D1DfHcNHMV7gn",
    "HYWo71Wk9PNDe5sBaRKazPnVyGnQDiwgXCFKvgAQ1ENp",
    "fag88ZkBfwbbD1cW7PvFvob8N2pNLFRhz4EkcowxvPd",
    "CgmwCcCoF5YNhWrVBz2R2iH4MopfvYLfxLgSZsrnemi6",
    "EFmDSnRbFCHkUz3z9vVMahma725xe8zXoT1ru7ymwAgz",
    "8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6",
    "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
    "8zFZHuSRuDpuAR7J6FzwyF3vKNx4CVW3DFHJerQhc7Zd",
    "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t",
    "A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR",
    "GJA1HEbxGnqBhBifH9uQauzXSB53to5rhDrzmKxhSU65",
    "89HbgWduLwoxcofWpmn1EiF9wEdpgkNDEyPjzZ72mkDi",
    "5jVhe5N3PGc5Bbw7FQL9d58rJbZN9x4ZGfZF9gStuSxx",
    "BTeqNydtKyDaSxQNRm8ByaUDPK3cpQ1FsXMtaF1Hfaom",
    "gangJEP5geDHjPVRhDS5dTF5e6GtRvtNogMEEVs91RV",
    "87rRdssFiTJKY4MGARa4G5vQ31hmR7MxSmhzeaJ5AAxJ",
    "2X4H5Y9C4Fy6Pf3wpq8Q4gMvLcWvfrrwDv2bdR8AAwQv",
    "HdxkiXqeN6qpK2YbG51W23QSWj3Yygc1eEk2zwmKJExp",
    "4BdKaxN8G6ka4GYtQQWk4G4dZRUTX2vQH9GcXdBREFUk",
    "3kebnKw7cPdSkLRfiMEALyZJGZ4wdiSRvmoN4rD1yPzV",
    "75GMVrr2xfgAeybuNg1VMHqFE3GTFJLzEHo6xC4MwUzF",
    "623LJRxYyhE6fpkVbJhF9PwNV2gTCkHgkLjSFFdpump",
    "6ujZxnphRxTqveaQtLAQHFoWz16xhLWZbTijcgZN4fRp",
    "79hZEQNbh8D3zo8u1B2rtVZ1igBGPaBqYpUmSkvBSsd3",
    "CAxg2BNNLa5rEHpM7oY9nr5jsoSsXaDyTgZP5eHcCGHz",
    "H1HtbqBEWVACPkjLbYWWdLQKLsJJonDR4weLHMzEzykd",
    "54YSQXJQCSNZDVtCpVfS9fmxZwr7WYDuPXsyocbbMb7d",
    "CshBQzeUCNAGSTtF55j73TXPuEKheSLTtGPCQFFPvjGi",
    "C2RosgbFvpcc5Ew64tsAihFsomAvyeL1i4KcAcZvBfxr",
    "FD4uTdPmwTmHvi43Qs6yw9CQYUtXud7njXiJaw1X7K3",
]

MIN_MARKET_CAP     = 1000
MAX_MARKET_CAP     = 3_000_000
MIN_LIQUIDITY      = 1000
CHECK_INTERVAL     = 120

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


def get_tokens_from_wallet(wallet_address):
    """Récupère tous les tokens d'un wallet via Helius RPC."""
    tokens = []
    try:
        r = requests.post(HELIUS_RPC_URL, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }, timeout=15)

        if r.status_code == 200:
            data = r.json()
            accounts = (data.get("result") or {}).get("value", [])
            for acc in accounts:
                try:
                    mint = (
                        acc.get("account", {})
                        .get("data", {})
                        .get("parsed", {})
                        .get("info", {})
                        .get("mint", "")
                    )
                    if mint and mint not in tokens:
                        tokens.append(mint)
                except:
                    continue
        else:
            print(f"  ⚠️ Helius HTTP {r.status_code} pour {wallet_address[:8]}...")

    except Exception as e:
        print(f"  ⚠️ Helius erreur pour {wallet_address[:8]}...: {e}")

    return tokens


def check_rugcheck(address, symbol="?"):
    try:
        r = requests.get(
            f"https://api.rugcheck.xyz/v1/tokens/{address}/report",
            timeout=15
        )
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
            top1_pct = float(top_holders[0].get("pct", 0) or 0) * 100
            if top1_pct > 50:
                return False, f"Top holder: {top1_pct:.1f}%"

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


def get_dexscreener_data(addresses, wallet):
    results = []
    for i in range(0, len(addresses), 30):
        batch = addresses[i:i+30]
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

                mc        = float(pair.get("marketCap", 0) or 0)
                liquidity = float((pair.get("liquidity") or {}).get("usd", 0) or 0)
                vol5m     = float((pair.get("volume") or {}).get("m5", 0) or 0)
                vol1h     = float((pair.get("volume") or {}).get("h1", 0) or 0)
                change5m  = float((pair.get("priceChange") or {}).get("m5", 0) or 0)
                change1h  = float((pair.get("priceChange") or {}).get("h1", 0) or 0)
                symbol    = base.get("symbol", "?")

                if not (MIN_MARKET_CAP <= mc <= MAX_MARKET_CAP):
                    continue
                if liquidity < MIN_LIQUIDITY:
                    continue

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
                    "name":      base.get("name", "Unknown"),
                    "symbol":    symbol,
                    "address":   addr,
                    "vol5m":     vol5m,
                    "vol1h":     vol1h,
                    "mc":        mc,
                    "liquidity": liquidity,
                    "change5m":  change5m,
                    "change1h":  change1h,
                    "wallet":    wallet,
                })
            except:
                pass
        time.sleep(1)

    return results


def fmt(n):
    if n is None: return "N/A"
    if n >= 1_000_000_000: return f"${n/1_000_000_000:.2f}B"
    if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
    if n >= 1_000: return f"${n/1_000:.1f}K"
    return f"${n:.0f}"


def send_discord(token):
    c5, c1  = token["change5m"], token["change1h"]
    color   = 0x00ff88 if c5 >= 0 else 0xff4444
    addr    = token["address"]
    wallet  = token["wallet"]

    embed = {
        "username":   "🦞 PumpCall BOT",
        "avatar_url": "https://pump.fun/favicon.ico",
        "embeds": [{
            "title": f"🚨 {token['name']} (${token['symbol']})",
            "color": color,
            "fields": [
                {"name": "👨‍💻 Dev Wallet",                               "value": f"`{wallet[:8]}...{wallet[-4:]}`", "inline": False},
                {"name": "💰 Market Cap",                                 "value": fmt(token["mc"]),        "inline": True},
                {"name": "💧 Liquidité",                                  "value": fmt(token["liquidity"]), "inline": True},
                {"name": "📊 Vol 5m",                                     "value": fmt(token["vol5m"]),     "inline": True},
                {"name": "📊 Vol 1h",                                     "value": fmt(token["vol1h"]),     "inline": True},
                {"name": "🟢 Change 5m" if c5 >= 0 else "🔴 Change 5m", "value": f"{c5:+.1f}%",          "inline": True},
                {"name": "🟢 Change 1h" if c1 >= 0 else "🔴 Change 1h", "value": f"{c1:+.1f}%",          "inline": True},
                {"name": "✅ RugCheck",                                   "value": "Vérifié",               "inline": True},
                {"name": "🔗 Links", "value": f"[DexScreener](https://dexscreener.com/solana/{addr}) • [Pump.fun](https://pump.fun/{addr}) • [Axiom](https://axiom.trade/meme/{addr}) • [GMGN](https://gmgn.ai/sol/token/{addr})", "inline": False},
                {"name": "📋 CA",  "value": f"`{addr}`",                                                    "inline": False},
                {"name": "🔎 Dev", "value": f"[Voir wallet](https://solscan.io/account/{wallet})",          "inline": False},
            ],
            "footer": {"text": f"PumpCall BOT • Dev Tracker • {datetime.utcnow().strftime('%H:%M UTC')}"},
        }]
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=embed, timeout=10)
        if r.status_code in [200, 204]:
            print(f"✅ Callé: {token['name']} (${token['symbol']}) | MC: {fmt(token['mc'])}")
            return True
        print(f"❌ Discord {r.status_code}")
    except Exception as e:
        print(f"❌ {e}")
    return False


def main():
    init_redis()
    print("🦞 PumpCall BOT — Dev Tracker démarré !")
    print(f"⚡ Helius RPC activé")
    print(f"👀 {len(DEV_WALLETS)} wallets trackés")
    print(f"🔄 Scan toutes les {CHECK_INTERVAL}s\n")

    wallet_tokens = {w: set() for w in DEV_WALLETS}

    # ── SCAN INITIAL : mémorise tout sans caller ──
    print("⏳ Initialisation — scan initial (pas de call)...")
    for wallet in DEV_WALLETS:
        try:
            addrs = get_tokens_from_wallet(wallet)
            wallet_tokens[wallet].update(addrs)
            for a in addrs:
                mark_seen(a)  # marque comme vus pour ne jamais les caller
            print(f"  ✅ {wallet[:8]}...{wallet[-4:]} — {len(addrs)} tokens mémorisés")
        except Exception as e:
            print(f"  ⚠️ Erreur init {wallet[:8]}: {e}")
        time.sleep(0.3)
    print(f"\n✅ Init terminée — {sum(len(v) for v in wallet_tokens.values())} tokens mémorisés au total")
    print("🟢 Surveillance active !\n")

    # ── BOUCLE PRINCIPALE ──
    while True:
        print(f"\n{'='*50}\n🔍 {datetime.utcnow().strftime('%H:%M:%S UTC')}\n{'='*50}")

        for wallet in DEV_WALLETS:
            print(f"\n👛 {wallet[:8]}...{wallet[-4:]}")
            try:
                current_tokens = get_tokens_from_wallet(wallet)

                # Seulement les tokens pas encore vus
                new_addresses = [
                    a for a in current_tokens
                    if a not in wallet_tokens[wallet] and not is_seen(a)
                ]

                # Met à jour la mémoire dans tous les cas
                wallet_tokens[wallet].update(current_tokens)

                if not new_addresses:
                    print(f"  ℹ️  Aucun nouveau token")
                    continue

                print(f"  🆕 {len(new_addresses)} nouveau(x) token(s) détecté(s) !")

                tokens = get_dexscreener_data(new_addresses, wallet)
                for token in tokens:
                    send_discord(token)
                    time.sleep(1.5)

            except Exception as e:
                print(f"  ⚠️ Erreur wallet {wallet[:8]}: {e}")

            time.sleep(0.3)

        print(f"\n⏳ Prochain scan dans {CHECK_INTERVAL}s...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
