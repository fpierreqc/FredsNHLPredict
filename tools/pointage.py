"""Pointages détaillés pour une liste de matchs, à partir de elo_current.json et du CSV de la saison.
Usage : python3 tools/pointage.py "CHI@BOS" "CGY@COL:away_b2b" "OTT@SJS:away_sub" ..."""
import sys, json; sys.path.insert(0, ".")
from elo_fred import EloFred, CONF
from score_fred import ScoreFred
from tools.analyse import load

def build_scores(csv="data/games_2026-27.csv"):
    sf = ScoreFred()
    for g in load(csv): sf.update(g["home"], g["away"], int(g["home_goals"]), int(g["away_goals"]))
    return sf

if __name__ == "__main__":
    m = EloFred.load("elo_current.json"); sf = build_scores()
    for arg in sys.argv[1:]:
        core, *flags = arg.split(":"); away, home = core.split("@")
        kw = {f: 1 for f in flags}
        p = m.prob_home(home, away, **kw); pick = home if p >= .5 else away
        t = sf.table(home, away, p); (hg, ag), _ = sf.predict(home, away, p)
        tops = "  ".join(f"{h}-{a} {v:.0%}" for (h, a), v in t["top"][:3])
        print(f"{away} @ {home} | {pick} {max(p,1-p):.0%}{' T' if abs(p-.5)>CONF else ''} | pointage {hg}-{ag} (dom-vis) | λ {t['lambda_home']:.2f}/{t['lambda_away']:.2f} | top: {tops} | >6,5 : {t['p_over65']:.0%} | favori par 2+ : {t['p_fav_by2']:.0%}")
