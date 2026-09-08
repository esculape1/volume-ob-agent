"""
Récupération des données OHLCV via ccxt (lecture seule, aucune clé API requise
pour les données de marché publiques).
"""
import ccxt
import pandas as pd


def get_exchange(exchange_id: str):
    """
    Instancie un exchange ccxt en mode public (pas de clé nécessaire).

    Cas particulier Binance : l'API principale (api.binance.com) bloque les
    requêtes venant de datacenters cloud américains (erreur 451 "restricted
    location"), ce qui inclut les serveurs GitHub Actions (Azure/AWS US).
    Binance fournit un miroir public dédié aux données de marché en lecture
    seule (pas de trading, pas de compte) qui n'est pas soumis à ce blocage :
    on bascule dessus automatiquement pour éviter le problème.
    """
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})
    if exchange_id == "binance":
        exchange.urls["api"]["public"] = "https://data-api.binance.vision/api/v3"
    return exchange


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


def fetch_ohlcv_extended(exchange, symbol: str, timeframe: str, total_candles: int) -> pd.DataFrame:
    """
    Récupère un historique plus long que la limite d'un seul appel (souvent
    500-1000 bougies max par requête chez la plupart des exchanges), en
    paginant vers le passé avec le paramètre `since`. Utilisé pour le
    backtest, qui a besoin de plus d'historique qu'une analyse en direct.
    """
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    all_rows = []
    # on part du présent et on remonte dans le temps par blocs de 1000 bougies max
    end_time = exchange.milliseconds()
    per_call = 1000

    while len(all_rows) < total_candles:
        remaining = total_candles - len(all_rows)
        fetch_size = min(per_call, remaining)
        since = end_time - fetch_size * timeframe_ms
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=fetch_size)
        if not batch:
            break
        all_rows = batch + all_rows
        end_time = batch[0][0]  # on continue de remonter avant la première bougie reçue
        if len(batch) < fetch_size:
            break  # l'exchange n'a plus d'historique plus ancien

    # dédoublonnage par timestamp au cas où deux appels se chevauchent
    seen = set()
    unique_rows = []
    for row in all_rows:
        if row[0] not in seen:
            seen.add(row[0])
            unique_rows.append(row)
    unique_rows.sort(key=lambda r: r[0])
    unique_rows = unique_rows[-total_candles:]

    df = pd.DataFrame(unique_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df
