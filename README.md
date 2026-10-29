# Bendevine — Équation Fred

Modèle de prédiction des matchs de la LNH (Elo adapté) derrière Bendevine.ca.

## Contenu

- `elo_fred.py` — le modèle : `backtest`, `predict`, `update`.
- `elo_current.json` — cotes au 27 octobre 2026 (reconstruites, ± 2-3 pts).
- `data/games_2026-27.csv` — 198 matchs de la saison avec gardiens substituts et prolongations.
- `data/elo_start_2026-27.json` — cotes de départ utilisées pour le rejeu.
- `docs/BILAN_2026-27.md` — bilan des prédictions et journal des modifications.
- `skills/equation-fred-quotidien/SKILL.md` — procédure quotidienne (Claude).

## Règles (28 octobre 2026)

K = 8 · domicile +25 · substitut −30 · deuxième match en deux soirs −30 · marge 1 + 0,5·ln(écart) · prolongation ×0,75 · tranché si |p − 0,5| > 0,08 · pointage indicatif 3-2.

## Exemples

```
python3 elo_fred.py backtest data/games_2026-27.csv --start data/elo_start_2026-27.json
python3 elo_fred.py predict MTL TOR --away-b2b
python3 elo_fred.py update MTL TOR 3 2 --ot
```

## À brancher

Remplacer `elo_current.json` par les vraies cotes issues de `elo_2025-26_final.json` (régressées d'un tiers vers 1500) et rejouer le CSV.
