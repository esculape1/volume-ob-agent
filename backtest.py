"""
Backtest de la stratégie Volume + Order Blocks sur données historiques.

Principe anti-biais (important) : à chaque bougie i de l'historique, on
appelle EXACTEMENT la même fonction signal_engine.evaluate() que le script
en direct, mais en ne lui donnant que les données JUSQU'À la bougie i
(df.iloc[:i+1]) — jamais les bougies futures. C'est ce qui garantit que le
backtest reflète fidèlement ce que le script aurait réellement signalé à
ce moment-là, sans tricher avec des informations qu'on n'aurait pas eues
en temps réel.

Limites connues (à garder en tête en lisant les résultats) :
- Suppose une exécution possible exactement au prix de clôture de la bougie
  de signal (en réalité : léger slippage possible).
- Ignore les frais de transaction et le funding (coûts de financement du
  levier sur les perpetuals) — les résultats réels seront donc légèrement
  inférieurs à ceux du backtest.
- Un seul trade ouvert à la fois par symbole.
- N'utilise pas de coûts de spread.
"""
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

import config as cfg
import data_fetcher
import signal_engine


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_index: int
    entry_time: str
    entry_price: float
    stop_loss: float
    take_profit: float
    exit_index: Optional[int] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    outcome: Optional[str] = None   # "win", "loss", "timeout"
    r_multiple: Optional[float] = None
    score: int = 0


def _check_exit(trade: Trade, bar: pd.Series) -> bool:
    """Vérifie si la bougie courante déclenche le stop ou la cible. Renvoie True si le trade est clôturé."""
    if trade.direction == "LONG":
        hit_stop = bar["low"] <= trade.stop_loss
        hit_target = bar["high"] >= trade.take_profit
        # en cas d'ambiguïté (les deux touchés sur la même bougie), on suppose
        # prudemment que le stop est touché en premier (hypothèse conservatrice)
        if hit_stop:
            trade.exit_price = trade.stop_loss
            trade.outcome = "loss"
            return True
        if hit_target:
            trade.exit_price = trade.take_profit
            trade.outcome = "win"
            return True
    else:  # SHORT
        hit_stop = bar["high"] >= trade.stop_loss
        hit_target = bar["low"] <= trade.take_profit
        if hit_stop:
            trade.exit_price = trade.stop_loss
            trade.outcome = "loss"
            return True
        if hit_target:
            trade.exit_price = trade.take_profit
            trade.outcome = "win"
            return True
    return False


def _r_multiple(trade: Trade) -> float:
    """Calcule le résultat en multiple du risque initial (R)."""
    risk = abs(trade.entry_price - trade.stop_loss)
    if risk == 0:
        return 0.0
    if trade.direction == "LONG":
        return (trade.exit_price - trade.entry_price) / risk
    return (trade.entry_price - trade.exit_price) / risk


def backtest_symbol(exchange, symbol: str, verbose: bool = True) -> list:
    """Backteste un symbole et renvoie la liste des trades clôturés (fermés ou expirés)."""
    df = data_fetcher.fetch_ohlcv_extended(exchange, symbol, cfg.TIMEFRAME, cfg.BACKTEST_CANDLES)
    if len(df) < 100:
        if verbose:
            print(f"{symbol} : historique insuffisant ({len(df)} bougies), symbole ignoré.")
        return []

    warmup = max(cfg.VOLUME_MA_PERIOD * 2, cfg.CMF_PERIOD * 2, cfg.ATR_PERIOD * 2, 50)
    trades = []
    open_trade: Optional[Trade] = None

    n = len(df)
    for i in range(warmup, n):
        bar = df.iloc[i]

        # 1. Si un trade est ouvert, vérifier s'il se clôture sur cette bougie
        if open_trade is not None:
            closed = _check_exit(open_trade, bar)
            if not closed and (i - open_trade.entry_index) >= cfg.BACKTEST_MAX_HOLD_BARS:
                open_trade.exit_price = bar["close"]
                open_trade.outcome = "timeout"
                closed = True
            if closed:
                open_trade.exit_index = i
                open_trade.exit_time = str(df.index[i])
                open_trade.r_multiple = _r_multiple(open_trade)
                trades.append(open_trade)
                open_trade = None
            continue  # un seul trade actif à la fois : pas de nouvelle entrée ce tour-ci

        # 2. Pas de trade ouvert -> chercher un nouveau signal en ne regardant QUE le passé
        window = df.iloc[: i + 1]
        sig = signal_engine.evaluate(window.copy(), symbol, cfg)
        if sig is not None:
            open_trade = Trade(
                symbol=symbol,
                direction=sig.direction,
                entry_index=i,
                entry_time=str(df.index[i]),
                entry_price=sig.current_price,
                stop_loss=sig.stop_loss,
                take_profit=sig.take_profit,
                score=sig.score,
            )

    if verbose:
        print(f"{symbol} : {len(trades)} trades clôturés sur {n - warmup} bougies analysées.")
    return trades


def compute_stats(trades: list) -> dict:
    """Calcule les statistiques de performance à partir d'une liste de trades clôturés."""
    if not trades:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "timeouts": 0,
            "win_rate_pct": 0.0, "avg_r": 0.0, "profit_factor": None,
            "total_r": 0.0, "max_drawdown_r": 0.0,
        }

    wins = [t for t in trades if t.outcome == "win"]
    losses = [t for t in trades if t.outcome == "loss"]
    timeouts = [t for t in trades if t.outcome == "timeout"]

    total_r = sum(t.r_multiple for t in trades)
    avg_r = total_r / len(trades)

    gross_win_r = sum(t.r_multiple for t in trades if t.r_multiple > 0)
    gross_loss_r = abs(sum(t.r_multiple for t in trades if t.r_multiple < 0))
    profit_factor = (gross_win_r / gross_loss_r) if gross_loss_r > 0 else None

    # équité cumulée en unités de R, pour calculer le drawdown max
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t.r_multiple
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    win_rate = len(wins) / len(trades) * 100

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "timeouts": len(timeouts),
        "win_rate_pct": round(win_rate, 1),
        "avg_r": round(avg_r, 3),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "total_r": round(total_r, 2),
        "max_drawdown_r": round(max_dd, 2),
    }


def print_report(symbol: str, stats: dict):
    print("\n" + "-" * 55)
    print(f"Résultats backtest — {symbol}")
    print("-" * 55)
    if stats["total_trades"] == 0:
        print("Aucun trade généré sur la période testée.")
        return
    print(f"Trades totaux       : {stats['total_trades']}")
    print(f"Gagnants / Perdants  : {stats['wins']} / {stats['losses']}  (timeouts: {stats['timeouts']})")
    print(f"Taux de réussite     : {stats['win_rate_pct']}%")
    print(f"Gain moyen par trade : {stats['avg_r']} R")
    pf = stats["profit_factor"]
    print(f"Profit factor        : {pf if pf is not None else 'N/A (aucune perte)'}")
    print(f"Résultat cumulé      : {stats['total_r']} R")
    print(f"Drawdown max         : {stats['max_drawdown_r']} R")

    # traduction concrète avec le risque par trade configuré
    equity_pct = stats["total_r"] * cfg.BACKTEST_RISK_PCT
    dd_pct = stats["max_drawdown_r"] * cfg.BACKTEST_RISK_PCT
    print(f"\nAvec un risque de {cfg.BACKTEST_RISK_PCT}% du capital par trade :")
    print(f"  -> résultat cumulé simulé : {round(equity_pct, 2)}% du capital de départ")
    print(f"  -> pire creux (drawdown)  : -{round(dd_pct, 2)}% du capital")


def export_trades_csv(all_trades: list, path: str = "backtest_trades.csv"):
    if not all_trades:
        print("Aucun trade à exporter.")
        return
    rows = [{
        "symbol": t.symbol, "direction": t.direction,
        "entry_time": t.entry_time, "entry_price": t.entry_price,
        "exit_time": t.exit_time, "exit_price": t.exit_price,
        "stop_loss": t.stop_loss, "take_profit": t.take_profit,
        "outcome": t.outcome, "r_multiple": round(t.r_multiple, 3) if t.r_multiple is not None else None,
        "score": t.score,
    } for t in all_trades]
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"\nDétail des {len(all_trades)} trades exporté vers : {path}")


def main():
    exchange = data_fetcher.get_exchange(cfg.EXCHANGE_ID)
    all_trades = []

    print(f"Backtest sur {cfg.BACKTEST_CANDLES} bougies ({cfg.TIMEFRAME}) pour : {', '.join(cfg.SYMBOLS)}")
    print("(cela peut prendre plusieurs minutes selon le nombre de symboles et de bougies)\n")

    for symbol in cfg.SYMBOLS:
        try:
            trades = backtest_symbol(exchange, symbol)
            all_trades.extend(trades)
            stats = compute_stats(trades)
            print_report(symbol, stats)
        except Exception as e:
            print(f"Erreur lors du backtest de {symbol} : {e}")

    print("\n" + "=" * 55)
    print("RÉSULTAT GLOBAL (tous symboles confondus)")
    print("=" * 55)
    global_stats = compute_stats(all_trades)
    print_report("Portefeuille global", global_stats)

    export_trades_csv(all_trades)

    print("\nRappel : ce backtest ignore les frais de transaction et le "
          "slippage. Les résultats réels seront un peu moins bons que ceux "
          "affichés ici. Ne considère une stratégie comme fiable qu'après "
          "un nombre de trades statistiquement significatif (au moins "
          "30-50 trades par symbole, idéalement plus).")


if __name__ == "__main__":
    main()
