"""
Test isolé : envoie un message Telegram de test, sans passer par l'analyse
de marché. Sert à vérifier que le token/chat_id sont corrects, indépendamment
de savoir si un signal de trading a été détecté ou non.

Usage local :
    python test_telegram.py

Usage sur GitHub Actions : déclenche le workflow manuellement (Run workflow)
en modifiant temporairement run.yml pour appeler ce script à la place de
main.py, ou ajoute un second workflow dédié si tu veux le garder en place.
"""
import config as cfg
import notifier

def main():
    print(f"TELEGRAM_ENABLED = {cfg.TELEGRAM_ENABLED}")
    print(f"TELEGRAM_BOT_TOKEN = {'(défini)' if cfg.TELEGRAM_BOT_TOKEN else '(VIDE)'}")
    print(f"TELEGRAM_CHAT_ID   = {cfg.TELEGRAM_CHAT_ID if cfg.TELEGRAM_CHAT_ID else '(VIDE)'}")

    if not cfg.TELEGRAM_ENABLED:
        print("\nTelegram est désactivé : token ou chat_id manquant. "
              "Vérifie tes variables d'environnement (GitHub Secrets) ou config.py.")
        return

    ok = notifier.send_telegram_message(
        cfg.TELEGRAM_BOT_TOKEN,
        cfg.TELEGRAM_CHAT_ID,
        "Test de l'agent Volume + Order Blocks : si tu reçois ce message, "
        "la connexion Telegram fonctionne correctement.",
    )
    if ok:
        print("\nSUCCÈS : message envoyé. Vérifie ton Telegram.")
    else:
        print("\nÉCHEC : le message n'a pas pu être envoyé. Vérifie le token "
              "et le chat_id (voir le message d'erreur au-dessus).")

if __name__ == "__main__":
    main()
