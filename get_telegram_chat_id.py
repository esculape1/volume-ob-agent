"""
Aide ponctuelle pour récupérer ton chat_id Telegram.

Étapes :
1. Crée ton bot avec @BotFather sur Telegram (voir README.md), récupère le TOKEN.
2. Envoie n'importe quel message à ton bot depuis Telegram (ex: "salut").
3. Remplace BOT_TOKEN ci-dessous par ton vrai token et lance ce script :
       python get_telegram_chat_id.py
4. Le script affiche ton chat_id -> colle-le dans config.py (TELEGRAM_CHAT_ID).
"""
import requests

BOT_TOKEN = "COLLE_TON_TOKEN_ICI"

def main():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if not data.get("ok") or not data.get("result"):
        print("Aucun message trouvé. As-tu bien envoyé un message à ton bot avant de lancer ce script ?")
        print("Réponse brute :", data)
        return
    chat_id = data["result"][-1]["message"]["chat"]["id"]
    print(f"Ton chat_id est : {chat_id}")
    print("Copie cette valeur dans config.py, dans TELEGRAM_CHAT_ID.")

if __name__ == "__main__":
    main()
