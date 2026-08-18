"""
Combine les indicateurs de volume et les order blocks actifs pour produire
un signal de confluence. Ne place AUCUN ordre : ce module ne fait que
générer une recommandation d'analyse, à valider et exécuter par toi-même.
"""
from dataclasses import dataclass
from typing import Optional
import indicators
import order_blocks as ob_module


@dataclass
class Signal:
    symbol: str
    direction: str          # "LONG" ou "SHORT"
    score: int               # score de confluence (sur ~5)
    max_score: int
    reasons: list
    entry_zone: tuple        # (bas, haut) de la zone d'entrée suggérée
    stop_loss: float
    take_profit: float
    suggested_leverage: float
    current_price: float
    timestamp: str


def _price_in_zone(price: float, ob: ob_module.OrderBlock) -> bool:
    return ob.bottom <= price <= ob.top


def evaluate(df, symbol: str, cfg) -> Optional[Signal]:
    """
    Évalue la dernière bougie disponible : le prix est-il dans un order
    block actif, avec confluence de volume favorable ? Renvoie un Signal
    ou None si aucune configuration valable n'est trouvée.
    """
    df = indicators.compute_all(df, cfg)
    obs = ob_module.detect_order_blocks(df, cfg)

    current_pos = len(df) - 1
    current_price = df["close"].iloc[-1]
    current_rvol = df["rvol"].iloc[-1]
    current_cmf = df["cmf"].iloc[-1]
    obv_direction = indicators.obv_trend(df, cfg.OBV_TREND_LOOKBACK)
    atr = df["atr"].iloc[-1]

    actives = ob_module.active_order_blocks(obs, current_pos, cfg.OB_MAX_AGE_CANDLES)

    best_signal = None

    for ob in actives:
        if not _price_in_zone(current_price, ob):
            continue  # le prix ne visite pas cette zone en ce moment

        reasons = []
        score = 0
        max_score = 5

        if ob.kind == "bullish":
            direction = "LONG"
            # 1. Volume au moment de l'impulsion qui a créé l'OB était-il fort ?
            impulse_rvol = df["rvol"].iloc[ob.candle_index_pos: ob.candle_index_pos + 3].max()
            if impulse_rvol and impulse_rvol >= cfg.RVOL_STRONG:
                score += 1
                reasons.append(f"Order block créé sur impulsion à fort volume (RVOL={impulse_rvol:.2f})")
            # 2. Volume actuel en zone de retour : faible = retracement sans conviction vendeuse = bon signe
            if current_rvol <= cfg.RVOL_WEAK:
                score += 1
                reasons.append(f"Volume faible sur le retour dans la zone (RVOL={current_rvol:.2f}) : peu de pression vendeuse")
            # 3. CMF positif ou proche de 0 = pression acheteuse sous-jacente
            if current_cmf > -0.05:
                score += 1
                reasons.append(f"CMF favorable ({current_cmf:.2f})")
            # 4. OBV en tendance haussière ou stable
            if obv_direction in ("up", "flat"):
                score += 1
                reasons.append(f"OBV en tendance {obv_direction}")
            # 5. Order block encore "frais" (récent)
            if (current_pos - ob.candle_index_pos) <= cfg.OB_MAX_AGE_CANDLES / 2:
                score += 1
                reasons.append("Order block récent (zone encore pertinente)")

            stop_loss = ob.bottom - atr * 0.25
            risk = current_price - stop_loss
            take_profit = current_price + risk * cfg.TARGET_RISK_REWARD

        else:  # bearish
            direction = "SHORT"
            impulse_rvol = df["rvol"].iloc[ob.candle_index_pos: ob.candle_index_pos + 3].max()
            if impulse_rvol and impulse_rvol >= cfg.RVOL_STRONG:
                score += 1
                reasons.append(f"Order block créé sur impulsion à fort volume (RVOL={impulse_rvol:.2f})")
            if current_rvol <= cfg.RVOL_WEAK:
                score += 1
                reasons.append(f"Volume faible sur le retour dans la zone (RVOL={current_rvol:.2f}) : peu de pression acheteuse")
            if current_cmf < 0.05:
                score += 1
                reasons.append(f"CMF favorable ({current_cmf:.2f})")
            if obv_direction in ("down", "flat"):
                score += 1
                reasons.append(f"OBV en tendance {obv_direction}")
            if (current_pos - ob.candle_index_pos) <= cfg.OB_MAX_AGE_CANDLES / 2:
                score += 1
                reasons.append("Order block récent (zone encore pertinente)")

            stop_loss = ob.top + atr * 0.25
            risk = stop_loss - current_price
            take_profit = current_price - risk * cfg.TARGET_RISK_REWARD

        if score < cfg.MIN_CONFLUENCE_SCORE:
            continue

        # Levier suggéré : proportionnel au score de confluence, borné par la config
        leverage_range = cfg.MAX_LEVERAGE - cfg.MIN_LEVERAGE
        suggested_leverage = cfg.MIN_LEVERAGE + leverage_range * (score / max_score)
        suggested_leverage = round(min(cfg.MAX_LEVERAGE, max(cfg.MIN_LEVERAGE, suggested_leverage)), 1)

        candidate = Signal(
            symbol=symbol,
            direction=direction,
            score=score,
            max_score=max_score,
            reasons=reasons,
            entry_zone=(ob.bottom, ob.top),
            stop_loss=round(stop_loss, 6),
            take_profit=round(take_profit, 6),
            suggested_leverage=suggested_leverage,
            current_price=round(current_price, 6),
            timestamp=str(df.index[-1]),
        )

        if best_signal is None or candidate.score > best_signal.score:
            best_signal = candidate

    return best_signal
