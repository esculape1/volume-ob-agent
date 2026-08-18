"""
Agent d'analyse Volume + Order Blocks — point d'entrée.

IMPORTANT :
- Ce script NE PLACE AUCUN ORDRE. Il analyse le marché et affiche des
  alertes de confluence (volume + order blocks) pour t'aider à décider.
  L'exécution reste 100% manuelle, chez ton broker/exchange.
- Ce n'est pas un conseil financier. Aucune stratégie ne garantit un
  résultat. Teste toujours en paper trading avant d'utiliser du capital réel,
  et backteste sur plusieurs mois avant de faire confiance aux signaux.

Usage :
    python main.py            # une analyse ponctuelle de tous les symboles
    python main.py --loop     # tourne en continu (toutes les X minutes, cf config.py)
"""
import sys
import time
import logging
from datetime import datetime

import config as cfg
import data_fetcher
import signal_engine
import notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("volume_ob_agent")


def analyze_once(exchange):
    signals = []
    for symbol in cfg.SYMBOLS:
        try:
            df = data_fetcher.fetch_ohlcv(exchange, symbol, cfg.TIMEFRAME, cfg.CANDLES_LOOKBACK)
            sig = signal_engine.evaluate(df, symbol, cfg)
            if sig:
                signals.append(sig)
                _print_signal(sig)
                if cfg.TELEGRAM_ENABLED:
                    notifier.send_telegram_message(
                        cfg.TELEGRAM_BOT_TOKEN,
                        cfg.TELEGRAM_CHAT_ID,
                        notifier.format_signal_message(sig),
                    )
            else:
                logger.info(f"{symbol} : aucune configuration de confluence suffisante en ce moment.")
        except Exception as e:
            logger.error(f"Erreur en analysant {symbol} : {e}")
    if not signals:
        logger.info("Aucun signal cette fois-ci sur les symboles suivis.")
    return signals


def _print_signal(sig: signal_engine.Signal):
    print("\n" + "=" * 60)
    print(f"SIGNAL {sig.direction} — {sig.symbol}  ({sig.timestamp})")
    print(f"Score de confluence : {sig.score}/{sig.max_score}")
    print(f"Prix actuel        : {sig.current_price}")
    print(f"Zone d'entrée (OB)  : {sig.entry_zone[0]:.6f} — {sig.entry_zone[1]:.6f}")
    print(f"Stop-loss suggéré   : {sig.stop_loss}")
    print(f"Take-profit suggéré : {sig.take_profit}")
    print(f"Levier suggéré      : x{sig.suggested_leverage} (plafond configuré : x{cfg.MAX_LEVERAGE})")
    print("Raisons de confluence :")
    for r in sig.reasons:
        print(f"  - {r}")
    print("=" * 60)
    print("Rappel : signal informatif uniquement. Vérifie le contexte avant d'exécuter.\n")


def main():
    exchange = data_fetcher.get_exchange(cfg.EXCHANGE_ID)
    loop_mode = "--loop" in sys.argv

    if not loop_mode:
        logger.info("Analyse ponctuelle en cours...")
        analyze_once(exchange)
        return

    logger.info(f"Mode continu activé — analyse toutes les {cfg.POLL_INTERVAL_SECONDS // 60} minutes. Ctrl+C pour arrêter.")
    while True:
        logger.info(f"--- Nouvelle analyse : {datetime.now()} ---")
        analyze_once(exchange)
        time.sleep(cfg.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
