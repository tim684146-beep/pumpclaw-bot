# 🦞 PumpCall BOT

Bot Discord qui call automatiquement les tokens pump.fun avec gros volume.

## Setup

### 1. Webhook Discord
- Discord → ton serveur → channel → Paramètres → Intégrations → Webhooks → Nouveau webhook
- Copie l'URL et remplace `METS_TON_WEBHOOK_ICI` dans bot.py

### 2. Déployer sur Railway (gratuit)
1. Crée un compte sur railway.app
2. New Project → Deploy from GitHub repo
3. Upload les fichiers ou connecte GitHub
4. Le bot démarre automatiquement !

### 3. Personnaliser les filtres dans bot.py
- `MIN_VOLUME_5M` : volume minimum 5 minutes
- `MIN_VOLUME_1H` : volume minimum 1 heure  
- `MIN_MARKET_CAP` : market cap minimum
- `MAX_MARKET_CAP` : market cap maximum
- `CHECK_INTERVAL` : fréquence de scan (secondes)
