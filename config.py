"""
Configuration de l'agent Volume + Order Blocks.
Modifie ces paramètres selon tes préférences.
"""
import os

# --- Marché ---
EXCHANGE_ID = "binance"          # exchange ccxt à utiliser
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "BNB/USDT", "XRP/USDT", "ADA/USDT",
]  # paires à surveiller — ajoute/enlève librement (voir README pour la syntaxe)
TIMEFRAME = "4h"                 # unité de temps des bougies (1h, 4h, 1d, ...)
CANDLES_LOOKBACK = 300           # nombre de bougies historiques à charger

# --- Détection de structure / order blocks ---
SWING_LOOKBACK = 3               # nb de bougies de chaque côté pour définir un swing high/low (fractal)
DISPLACEMENT_MIN_PCT = 1.5       # % de mouvement mini pour considérer un déplacement "impulsif"
OB_MAX_AGE_CANDLES = 80          # au-delà, on considère l'order block trop vieux / non pertinent

# --- Indicateurs de volume ---
VOLUME_MA_PERIOD = 20            # période de la moyenne mobile du volume
RVOL_STRONG = 1.5                # seuil de volume relatif jugé "fort"
RVOL_WEAK = 0.7                  # seuil de volume relatif jugé "faible"
CMF_PERIOD = 20                  # période du Chaikin Money Flow
OBV_TREND_LOOKBACK = 14          # nb de bougies pour juger la tendance de l'OBV
ATR_PERIOD = 14                  # période de l'ATR (pour stop / volatilité)

# --- Gestion du risque (informatif, tu appliques toi-même) ---
RISK_PER_TRADE_PCT = 1.0         # % du capital risqué par trade (suggestion)
MAX_LEVERAGE = 4                 # levier max que tu t'autorises
MIN_LEVERAGE = 2
TARGET_RISK_REWARD = 2.0         # ratio gain/risque visé par défaut pour la cible suggérée

# --- Score de confluence minimum pour déclencher une alerte ---
MIN_CONFLUENCE_SCORE = 3         # sur un total de ~5 critères (voir signal_engine.py)

# --- Boucle ---
POLL_INTERVAL_SECONDS = 900      # 15 min entre deux analyses en mode continu

# --- Notifications Telegram (optionnel) ---
# En local : tu peux renseigner directement TOKEN et CHAT_ID ci-dessous.
# Sur GitHub Actions : NE JAMAIS écrire de vraies valeurs ici. Elles sont
# lues automatiquement depuis les "Secrets" GitHub (variables d'environnement),
# donc laisse les valeurs par défaut vides dans ce fichier si tu utilises GitHub.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
