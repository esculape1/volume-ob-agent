# Agent Volume + Order Blocks — Signaux d'analyse crypto

Script Python qui surveille des paires crypto sur Binance (données publiques,
aucune clé API requise), calcule des indicateurs de volume, détecte des
order blocks algorithmiquement, et affiche des alertes de confluence.

## ⚠️ Ce que cet outil fait — et ne fait PAS

- **Fait** : analyse les marchés en lecture seule, affiche des signaux
  (direction, zone d'entrée, stop, cible, score de confluence) dans le terminal.
- **Ne fait PAS** : il ne place, ne modifie et n'annule **aucun ordre**. Aucune
  clé API de trading n'est utilisée. Toute décision et exécution reste manuelle.
- **N'est pas un conseil financier.** C'est un outil d'aide à la lecture de
  marché, basé sur des heuristiques (volume + structure de prix). Aucune
  stratégie ne garantit un résultat, et le levier amplifie les pertes autant
  que les gains.

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

Analyse ponctuelle (une passe sur tous les symboles configurés) :
```bash
python main.py
```

Mode continu (relance l'analyse toutes les X minutes, cf. `config.py`) :
```bash
python main.py --loop
```

## Configuration (`config.py`)

| Paramètre | Rôle |
|---|---|
| `SYMBOLS` | Liste des paires à surveiller (ex: `BTC/USDT`) |
| `TIMEFRAME` | Unité de temps des bougies (`1h`, `4h`, `1d`...) |
| `SWING_LOOKBACK` | Sensibilité de détection des swings/fractals |
| `DISPLACEMENT_MIN_PCT` | Amplitude minimum pour valider un order block |
| `RVOL_STRONG` / `RVOL_WEAK` | Seuils de volume relatif |
| `MIN_CONFLUENCE_SCORE` | Score minimum (sur 5) pour déclencher une alerte |
| `MIN_LEVERAGE` / `MAX_LEVERAGE` | Bornes du levier suggéré affiché (2 à 4 par défaut) |
| `TARGET_RISK_REWARD` | Ratio gain/risque utilisé pour calculer la cible suggérée |

## Comment lire un signal

```
SIGNAL LONG — BTC/USDT  (2026-08-17 12:00:00)
Score de confluence : 4/5
Prix actuel        : 61250.0
Zone d'entrée (OB)  : 60800.0 — 61100.0
Stop-loss suggéré   : 60550.0
Take-profit suggéré : 62450.0
Levier suggéré      : x3.2 (plafond configuré : x4)
Raisons de confluence :
  - Order block créé sur impulsion à fort volume (RVOL=2.10)
  - Volume faible sur le retour dans la zone (RVOL=0.55)
  - CMF favorable (0.12)
  - OBV en tendance up
```

Le **score de confluence** (sur 5) reflète combien de critères de volume
confirment l'order block :
1. Volume fort au moment de la création de l'order block (conviction initiale)
2. Volume faible sur le retour dans la zone (pas de contre-pression)
3. CMF orienté dans le sens du signal
4. OBV en tendance cohérente
5. Order block encore "récent" (zone pas trop ancienne)

Le stop et la cible sont des **suggestions calculées automatiquement**
(basées sur l'ATR et un ratio risque/rendement configurable) — vérifie-les
toujours par rapport au contexte du graphique avant d'agir.

## Étapes recommandées avant tout usage avec du capital réel

1. **Backtester** : faire tourner la logique sur plusieurs mois de données
   historiques et évaluer le taux de réussite réel avant de se fier aux signaux.
2. **Paper trading** : suivre les signaux "à blanc" pendant quelques semaines
   sans engager d'argent, pour évaluer leur pertinence dans les conditions
   de marché actuelles.
3. **Calibrer `config.py`** : les seuils par défaut sont des points de départ
   raisonnables, pas des valeurs optimales — ils doivent être ajustés à
   l'actif et au timeframe suivis.
4. **Ne jamais dépasser le risque par trade que tu es prêt à perdre**,
   surtout avec un levier de 2 à 4x.

## Recevoir les alertes sur Telegram

1. Ouvre Telegram, cherche **@BotFather** (le bot officiel de création de bots), démarre une conversation.
2. Tape `/newbot`, donne un nom à ton bot (ex: `MonAgentVolume`), puis un nom d'utilisateur qui doit finir par `bot` (ex: `mon_agent_volume_bot`).
3. BotFather te donne un **token** (une longue chaîne du type `123456789:ABC-...`). Copie-le.
4. Envoie n'importe quel message à ton nouveau bot (cherche-le par son nom d'utilisateur et écris-lui "salut").
5. Ouvre `get_telegram_chat_id.py`, remplace `COLLE_TON_TOKEN_ICI` par ton vrai token, sauvegarde, puis lance :
   ```
   python get_telegram_chat_id.py
   ```
   Il t'affiche ton `chat_id`.
6. Ouvre `config.py` et renseigne :
   ```python
   TELEGRAM_ENABLED = True
   TELEGRAM_BOT_TOKEN = "ton_token_ici"
   TELEGRAM_CHAT_ID = "ton_chat_id_ici"
   ```
7. Relance `python main.py` ou `python main.py --loop` : chaque signal détecté t'enverra désormais aussi un message Telegram, même si la fenêtre du script est en arrière-plan.

## Ajouter ou retirer des cryptos

Dans `config.py`, modifie la liste `SYMBOLS`. La syntaxe est toujours `"XXX/USDT"` (la crypto suivie de la paire de cotation). Exemples de paires valables sur Binance : `"DOGE/USDT"`, `"AVAX/USDT"`, `"LINK/USDT"`, `"LTC/USDT"`. Tu peux vérifier qu'une paire existe en la cherchant sur binance.com (marché Spot).

## Extension vers la BRVM

La BRVM n'a pas d'API publique de données de marché en temps réel comme
Binance. Pour adapter cet outil à la BRVM, il faudra soit :
- importer manuellement des fichiers CSV depuis brvm.org,
- soit construire un scraper dédié pour les cours quotidiens.
Ce sera l'objet d'une prochaine étape, une fois la version crypto validée.
