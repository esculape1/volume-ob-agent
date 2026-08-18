"""
Envoi d'alertes via un bot Telegram. Voir README.md pour la procédure
de création du bot et de récupération du chat_id.
"""
import requests
import logging

logger = logging.getLogger("volume_ob_agent")


def send_telegram_message(bot_token: str, chat_id: str, text: str):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Échec envoi Telegram ({resp.status_code}) : {resp.text}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi Telegram : {e}")


def format_signal_message(sig) -> str:
    lines = [
        f"SIGNAL {sig.direction} — {sig.symbol}",
        f"Score de confluence : {sig.score}/{sig.max_score}",
        f"Prix actuel : {sig.current_price}",
        f"Zone d'entrée : {sig.entry_zone[0]:.6f} — {sig.entry_zone[1]:.6f}",
        f"Stop-loss suggéré : {sig.stop_loss}",
        f"Take-profit suggéré : {sig.take_profit}",
        f"Levier suggéré : x{sig.suggested_leverage}",
        "",
        "Raisons :",
    ]
    lines += [f"- {r}" for r in sig.reasons]
    lines.append("")
    lines.append("Rappel : signal informatif uniquement, pas d'exécution automatique.")
    return "\n".join(lines)
