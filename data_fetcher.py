"""
Récupération des données OHLCV via ccxt (lecture seule, aucune clé API requise
pour les données de marché publiques).
"""
import ccxt
import pandas as pd


def get_exchange(exchange_id: str):
    """Instancie un exchange ccxt en mode public (pas de clé nécessaire)."""
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def fetch_ohlcv(exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Récupère les bougies OHLCV et renvoie un DataFrame indexé par date,
    colonnes: open, high, low, close, volume.
    """
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df
