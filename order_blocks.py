"""
Détection algorithmique des swings, des cassures de structure (Break of
Structure) et des order blocks (bullish / bearish).

Définition utilisée (heuristique standard "smart money concepts") :
- Un swing high/low est un point plus extrême que les N bougies de chaque côté (fractal).
- Un Break of Structure (BOS) haussier = clôture au-dessus du dernier swing high.
- Un Break of Structure (BOS) baissier = clôture en dessous du dernier swing low.
- L'order block associé = la dernière bougie de sens opposé au mouvement,
  juste avant le déplacement impulsif qui a produit le BOS.
"""
from dataclasses import dataclass
import pandas as pd


@dataclass
class OrderBlock:
    kind: str          # "bullish" ou "bearish"
    index: pd.Timestamp
    top: float
    bottom: float
    candle_index_pos: int   # position entière dans le DataFrame (pour calculer l'âge)
    displacement_pct: float
    mitigated: bool = False  # True si le prix est déjà revenu combler la zone


def find_swings(df: pd.DataFrame, lookback: int):
    """Repère les swing highs et swing lows (fractals)."""
    highs = df["high"]
    lows = df["low"]
    swing_high_idx = []
    swing_low_idx = []
    n = len(df)
    for i in range(lookback, n - lookback):
        window_high = highs.iloc[i - lookback: i + lookback + 1]
        window_low = lows.iloc[i - lookback: i + lookback + 1]
        if highs.iloc[i] == window_high.max():
            swing_high_idx.append(i)
        if lows.iloc[i] == window_low.min():
            swing_low_idx.append(i)
    return swing_high_idx, swing_low_idx


def detect_order_blocks(df: pd.DataFrame, cfg) -> list:
    """
    Parcourt le DataFrame, détecte les BOS haussiers/baissiers et extrait
    l'order block correspondant. Renvoie une liste d'OrderBlock, du plus
    ancien au plus récent.
    """
    lookback = cfg.SWING_LOOKBACK
    swing_high_idx, swing_low_idx = find_swings(df, lookback)

    order_blocks = []
    last_swing_high = None
    last_swing_low = None

    swing_high_set = set(swing_high_idx)
    swing_low_set = set(swing_low_idx)

    n = len(df)
    for i in range(lookback, n):
        if i in swing_high_set:
            last_swing_high = df["high"].iloc[i]
        if i in swing_low_set:
            last_swing_low = df["low"].iloc[i]

        close = df["close"].iloc[i]

        # --- BOS haussier : clôture au-dessus du dernier swing high connu ---
        if last_swing_high is not None and close > last_swing_high:
            ob_pos = _find_last_opposite_candle(df, i, bullish_move=True)
            if ob_pos is not None:
                displacement_pct = _displacement_pct(df, ob_pos, i)
                if displacement_pct >= cfg.DISPLACEMENT_MIN_PCT:
                    candle = df.iloc[ob_pos]
                    order_blocks.append(OrderBlock(
                        kind="bullish",
                        index=df.index[ob_pos],
                        top=candle["high"],
                        bottom=candle["low"],
                        candle_index_pos=ob_pos,
                        displacement_pct=displacement_pct,
                    ))
            last_swing_high = None  # structure "consommée", on attend le prochain swing

        # --- BOS baissier : clôture en dessous du dernier swing low connu ---
        if last_swing_low is not None and close < last_swing_low:
            ob_pos = _find_last_opposite_candle(df, i, bullish_move=False)
            if ob_pos is not None:
                displacement_pct = _displacement_pct(df, ob_pos, i)
                if displacement_pct >= cfg.DISPLACEMENT_MIN_PCT:
                    candle = df.iloc[ob_pos]
                    order_blocks.append(OrderBlock(
                        kind="bearish",
                        index=df.index[ob_pos],
                        top=candle["high"],
                        bottom=candle["low"],
                        candle_index_pos=ob_pos,
                        displacement_pct=displacement_pct,
                    ))
            last_swing_low = None

    _mark_mitigated(df, order_blocks)
    return order_blocks


def _find_last_opposite_candle(df: pd.DataFrame, bos_pos: int, bullish_move: bool, max_search: int = 15):
    """
    Cherche, en remontant depuis la bougie de cassure (bos_pos), la dernière
    bougie de couleur opposée au mouvement -> c'est l'order block candidat.
    """
    start = max(0, bos_pos - max_search)
    for i in range(bos_pos, start - 1, -1):
        candle = df.iloc[i]
        is_bearish_candle = candle["close"] < candle["open"]
        is_bullish_candle = candle["close"] > candle["open"]
        if bullish_move and is_bearish_candle:
            return i
        if not bullish_move and is_bullish_candle:
            return i
    return None


def _displacement_pct(df: pd.DataFrame, ob_pos: int, bos_pos: int) -> float:
    """% de mouvement entre la clôture de l'order block et la bougie de cassure."""
    start_price = df["close"].iloc[ob_pos]
    end_price = df["close"].iloc[bos_pos]
    if start_price == 0:
        return 0.0
    return abs(end_price - start_price) / start_price * 100


def _mark_mitigated(df: pd.DataFrame, order_blocks: list):
    """
    Marque un order block comme invalidé si le prix a, depuis sa formation,
    CLÔTURÉ au-delà de la zone opposée (preuve que le niveau a été cassé,
    pas juste retesté). Un simple retour dans la zone (mèche ou clôture à
    l'intérieur) ne suffit pas à invalider le block : c'est précisément la
    configuration qu'on cherche à détecter comme signal d'entrée.
    """
    for ob in order_blocks:
        after = df.iloc[ob.candle_index_pos + 1:]
        if ob.kind == "bullish":
            broken = after[after["close"] < ob.bottom]
        else:
            broken = after[after["close"] > ob.top]
        ob.mitigated = len(broken) > 0


def active_order_blocks(order_blocks: list, current_pos: int, max_age: int) -> list:
    """Filtre les order blocks encore 'valides' : non mitigés et pas trop vieux."""
    return [
        ob for ob in order_blocks
        if not ob.mitigated and (current_pos - ob.candle_index_pos) <= max_age
    ]
