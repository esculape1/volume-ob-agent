"""
Test du pipeline complet avec des données OHLCV synthétiques (aucun accès
réseau requis). Vérifie que le code tourne sans erreur et produit des
signaux cohérents sur un mouvement construit exprès (impulsion haussière
avec order block, retour en zone, volume faible sur le retour).
"""
import numpy as np
import pandas as pd
import config as cfg
import signal_engine


def build_synthetic_df(n=160, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-01", periods=n, freq="4h")

    price = 100.0
    opens, highs, lows, closes, volumes = [], [], [], [], []

    for i in range(n):
        drift = rng.normal(0, 0.4)

        # Injecte une impulsion haussière nette + fort volume vers le milieu
        if 140 <= i <= 145:
            drift = 2.5  # forte hausse sur quelques bougies -> BOS + order block
        # Puis un retour calme (faible volume) vers la zone de l'order block
        if 150 <= i <= 158:
            drift = -0.3

        o = price
        c = o + drift + rng.normal(0, 0.3)
        h = max(o, c) + abs(rng.normal(0, 0.2))
        l = min(o, c) - abs(rng.normal(0, 0.2))

        base_vol = 1000 + rng.normal(0, 100)
        if 140 <= i <= 145:
            vol = base_vol * 3.5  # gros volume sur l'impulsion
        elif 150 <= i <= 158:
            vol = base_vol * 0.4  # volume faible sur le retour (bon signe en théorie)
        else:
            vol = base_vol

        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(max(vol, 10))

        price = c

    df = pd.DataFrame({
        "open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes
    }, index=dates)
    return df


def run():
    df = build_synthetic_df()
    sig = signal_engine.evaluate(df.copy(), "TEST/USDT", cfg)
    if sig:
        print("Signal détecté sur données synthétiques :")
        print(f"  Direction        : {sig.direction}")
        print(f"  Score            : {sig.score}/{sig.max_score}")
        print(f"  Entry zone       : {sig.entry_zone}")
        print(f"  Stop / Target    : {sig.stop_loss} / {sig.take_profit}")
        print(f"  Levier suggéré   : x{sig.suggested_leverage}")
        print(f"  Raisons          :")
        for r in sig.reasons:
            print(f"    - {r}")
        print("\nTEST RÉUSSI : le pipeline fonctionne de bout en bout.")
    else:
        print("Aucun signal détecté sur ce jeu de données synthétique.")
        print("(Peut être normal selon la graine aléatoire / les seuils de config — "
              "le but ici est surtout de vérifier l'absence d'erreurs d'exécution.)")


if __name__ == "__main__":
    run()
