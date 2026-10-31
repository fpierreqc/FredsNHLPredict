"""Pointage Fred — prédiction du pointage final, couche au-dessus de l'Elo.

Idée : total de buts attendu = attaque/défense des deux équipes (moyennes mobiles régressées vers la ligue),
écart attendu = fonction de la probabilité Elo. Deux Poisson indépendantes, puis on choisit le pointage
le plus probable PARMI ceux où le gagnant prédit gagne (cohérence avec le choix du gagnant).
Les buts en prolongation/fusillade sont comptés (écart 1) comme au tableau.
"""
import math
from collections import defaultdict

SPARAMS = dict(
    PRIOR=20,       # matchs fictifs à la moyenne de la ligue (régression)
    LEAGUE=3.05,    # buts par équipe par match (prior de départ)
    DIFF=1.10,      # écart attendu = DIFF * log-odds(p)  (buts)
    MAXG=9,
)

def pois(lam, k): return math.exp(-lam) * lam ** k / math.factorial(k)

class ScoreFred:
    def __init__(self, params=None):
        self.p = dict(SPARAMS, **(params or {}))
        self.gf = defaultdict(float); self.ga = defaultdict(float); self.gp = defaultdict(int)
        self.lg_goals = 0.0; self.lg_games = 0

    def league(self):
        return (self.lg_goals + 2 * self.p["PRIOR"] * self.p["LEAGUE"]) / (2 * self.lg_games + 2 * self.p["PRIOR"]) if True else self.p["LEAGUE"]

    def rate(self, team, side):
        L = self.league(); P = self.p["PRIOR"]
        tot = (self.gf if side == "f" else self.ga)[team]
        return (tot + P * L) / (self.gp[team] + P)

    def lambdas(self, home, away, p_home):
        L = self.league()
        # total attendu : attaque de l'un × défense de l'autre, normalisé
        lh = self.rate(home, "f") * self.rate(away, "a") / L
        la = self.rate(away, "f") * self.rate(home, "a") / L
        total = lh + la
        p = min(max(p_home, 0.02), 0.98)
        diff = self.p["DIFF"] * math.log(p / (1 - p))
        lh, la = (total + diff) / 2, (total - diff) / 2
        return max(lh, 0.4), max(la, 0.4)

    def predict(self, home, away, p_home, pick_home=None):
        """Pointage le plus probable (buts domicile, buts visiteur), cohérent avec le gagnant prédit.
        La masse des « nuls » est redistribuée au favori à l'écart 1 (prolongation)."""
        t = self.table(home, away, p_home)
        return t["top"][0][0], (t["lambda_home"], t["lambda_away"])

    def update(self, home, away, hg, ag):
        self.gf[home] += hg; self.ga[home] += ag; self.gf[away] += ag; self.ga[away] += hg
        self.gp[home] += 1; self.gp[away] += 1
        self.lg_goals += hg + ag; self.lg_games += 1

    def table(self, home, away, p_home):
        """Distribution complète : top pointages, P(total > 6,5), P(écart ≥ 2 pour le favori)."""
        lh, la = self.lambdas(home, away, p_home); M = self.p["MAXG"]; pick_home = p_home >= .5
        grid = {(h, a): pois(lh, h) * pois(la, a) for h in range(M + 1) for a in range(M + 1)}
        # les nuls n'existent pas : on redistribue leur masse au favori (prolongation) à l'écart 1
        for k in range(M):
            pr = grid.pop((k, k)); tgt = (k + 1, k) if pick_home else (k, k + 1)
            grid[tgt] = grid.get(tgt, 0) + pr
        z = sum(grid.values()); grid = {k: v / z for k, v in grid.items()}
        top = sorted(grid.items(), key=lambda x: -x[1])[:5]
        over = sum(v for (h, a), v in grid.items() if h + a > 6.5)
        fav2 = sum(v for (h, a), v in grid.items() if (h - a if pick_home else a - h) >= 2)
        home_win = sum(v for (h, a), v in grid.items() if h > a)
        return dict(lambda_home=lh, lambda_away=la, top=top, p_over65=over, p_fav_by2=fav2, p_home_poisson=home_win)
