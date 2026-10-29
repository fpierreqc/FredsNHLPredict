---
name: "equation-fred-quotidien"
description: "Cycle quotidien de prédictions LNH avec l'Équation Fred (Elo) : gardiens, gagnant, pointage, comparaison aux résultats et bilan cumulatif. À utiliser quand Fred demande de prédire ou de comparer des matchs."
---

# Équation Fred — cycle quotidien

Répondre en français québécois, conclusion d'abord, tableaux courts.

## 1. Le modèle (ne pas modifier sans demande explicite)

- Elo Fred : K=8, domicile +25, marge de victoire 1 + 0,5·ln(écart), prolongation ×0,75 (tirs de barrage inclus).
- Ajustement total (points Elo, du point de vue de l'équipe locale) : +25 domicile, +30 si le visiteur a un substitut devant le filet, −30 si c'est le local, +30 si le visiteur joue un deuxième match en deux soirs, −30 si c'est le local.
- Probabilité domicile : 1 / (1 + 10^(−(Elo_dom − Elo_vis + ajustement) / 400)).
- Match « tranché » : |p − 0,5| > 0,08. Les mises ne touchent que les tranchés.
- Deuxième match en deux soirs (adopté le 28 octobre 2026) : l'équipe qui a joué la veille prend −30. Effet mesuré sur 2025-26 (45,8 % de victoires) et sur 2026-27 (42 %).
- Gardien, numéro 1 :
  - Tant que l'équipe a joué moins de 5 matchs : celui de la saison précédente s'il est encore avec l'équipe et disponible, sinon le partant du match d'ouverture.
  - À partir de 5 matchs d'équipe : le gardien qui a le plus de départs cette saison.
  - Si le numéro 1 est blessé, suspendu, échangé ou indisponible à long terme, son remplaçant attitré devient le numéro 1. Un numéro 1 acquis par échange devient le numéro 1 de sa nouvelle équipe dès son premier départ.
  - Tandem à parts égales (écart de départs ≤ 1) : aucun des deux n'est substitut.
  - Tout autre partant = substitut, −30. En cas de doute, le signaler à Fred au lieu de trancher en silence.
- Pointage : 3-2 dans le sens du gagnant prédit, pour tous les matchs. C'est le pointage le plus fréquent de la LNH ; attendre environ 10 % de pointages exacts, pas plus. Étiqueter « indicatif ».
- Codes d'équipes : VEG pour Vegas (VGK accepté), NJD, SJS, LAK, TBL.

## 2. Les cotes

- Source de vérité : `elo_current.json` (ou `elo_2025-26_final.json`, régressé d'un tiers vers 1500) sur le Mac mini de Fred.
- Si le fichier n'est pas accessible, le dire en tête de réponse et préciser que les cotes sont reconstruites (± 2-3 points). Ne jamais présenter des cotes approximatives comme exactes.
- Faire les calculs dans un script, jamais de tête.

## 3. Procédure

1. Matchs et résultats : outil de données sportives (scores LNH). Il ne garde que quelques jours ; pour les dates plus anciennes et pour les prolongations, utiliser `https://www.hockey-reference.com/leagues/NHL_2027_games.html` (colonne OT/SO), ou les statistiques du match (buts en prolongation, tirs de barrage).
2. Gardiens : `https://www.dailyfaceoff.com/starting-goalies/AAAA-MM-JJ`. Si le site refuse, passer par une recherche web (DFOFantasy sur X, GamedayTweets, NHL.com « On Tap ») et vérifier dans les sommaires de match. Noter le statut (confirmé, probable, non confirmé) et les deuxièmes matchs en deux soirs.
3. Prédire chaque match : gagnant, probabilité, tranché ou non, pointage. Indiquer l'effet d'un changement de gardien quand il ferait basculer un match autour du seuil.
4. Matchs à venir : livrer les prédictions avant la première mise au jeu, puis planifier un suivi une quinzaine de minutes après la fin prévue du dernier match (début + 3 h). Ne jamais réécrire une prédiction une fois le match commencé.
5. Comparer aux résultats, mettre à jour les cotes des équipes qui ont joué, lister les ratés tranchés et leur cause probable.
6. Bilan cumulatif.

## 4. Bilan

- Toujours donner : tous les matchs, tranchés, non tranchés, pointages exacts, en nombre et en pourcentage, plus le détail par soirée.
- Séparer les prédictions faites avant le match de celles calculées après coup, et le dire clairement.
- Vérifier que la somme des lignes par soirée égale le total avant de publier.
- Repères : Vegas et MoneyPuck font 58-63 % ; le modèle a fait 58 % au total et 64 % sur les tranchés en validation.

## 5. Garde-fous

- Pas de changement de paramètre sur un petit échantillon ; toute idée se teste d'abord sur les CSV 2024-25 et 2025-26, ou doit être confirmée sur deux saisons.
- Candidat en attente : domicile +50 (meilleur logloss sur 2026-27, mais précision plus basse sur les tranchés hors échantillon). À tester sur les CSV avant d'adopter.
- Les 20 premiers matchs de chaque équipe sont une période de calibration.
- Si une donnée manque (gardien non confirmé, match non terminé, pointage provisoire), l'écrire plutôt que deviner.