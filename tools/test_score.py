"""Compare les règles de pointage sur la saison : 3-2 fixe, 4-2/3-2 selon la cote, Poisson (ScoreFred) et variantes."""
import sys, csv, json, datetime, itertools
sys.path.insert(0, ".")
from elo_fred import EloFred, CONF
from score_fred import ScoreFred
from tools.analyse import load, prev

def run(G, start, score_rule, sparams=None):
    m = EloFred(json.load(open(start))["ratings"]); sf = ScoreFred(sparams); last = {}
    ex = tot_err = diff_err = winner_ok = 0; n = 0; pred_scores = {}
    for g in G:
        d, h, a = g["date"], g["home"], g["away"]; hg, ag = int(g["home_goals"]), int(g["away_goals"]); ot = g["ot"] == "1"
        ph = m.prob_home(h, a, home_sub=int(g["home_sub"]), away_sub=int(g["away_sub"]),
                         home_b2b=int(last.get(h) == prev(d)), away_b2b=int(last.get(a) == prev(d)))
        pick_home = ph >= .5
        sc = score_rule(sf, h, a, ph, pick_home)
        ex += sc == (hg, ag); tot_err += abs(sum(sc) - hg - ag); diff_err += abs((sc[0]-sc[1]) - (hg-ag)); n += 1
        pred_scores[tuple(sorted(sc, reverse=True))] = pred_scores.get(tuple(sorted(sc, reverse=True)), 0) + 1
        m.update(h, a, hg, ag, ot, ph=ph); sf.update(h, a, hg, ag); last[h] = last[a] = d
    return dict(exact=ex, n=n, mae_total=tot_err/n, mae_diff=diff_err/n, dist=sorted(pred_scores.items(), key=lambda x: -x[1])[:5])

def fixed32(sf, h, a, ph, pick): return (3, 2) if pick else (2, 3)
def conf42(sf, h, a, ph, pick):
    s = (4, 2) if abs(ph - .5) > CONF else (3, 2); return s if pick else s[::-1]
def poisson(sf, h, a, ph, pick): return sf.predict(h, a, ph, pick)[0]
def poisson_round(sf, h, a, ph, pick):  # arrondi des lambdas, forcé cohérent
    (lh, la) = sf.lambdas(h, a, ph); hg, ag = round(lh), round(la)
    if pick and hg <= ag: hg = ag + 1
    if not pick and ag <= hg: ag = hg + 1
    return (hg, ag)

if __name__ == "__main__":
    G = load("data/games_2026-27.csv"); S = "data/elo_start_2026-27.json"
    fmt = lambda r: f"exact {r['exact']}/{r['n']} ({r['exact']/r['n']:.1%}) | EAM total {r['mae_total']:.2f} | EAM écart {r['mae_diff']:.2f} | {r['dist']}"
    print("3-2 fixe       ", fmt(run(G, S, fixed32)))
    print("4-2 si tranché ", fmt(run(G, S, conf42)))
    print("Poisson défaut ", fmt(run(G, S, poisson)))
    print("Poisson arrondi", fmt(run(G, S, poisson_round)))
    print("--- grille Poisson (PRIOR, DIFF) ---")
    for P, D in itertools.product((10, 20, 40, 1000), (0.6, 0.9, 1.1, 1.4, 1.8)):
        r = run(G, S, poisson, dict(PRIOR=P, DIFF=D)); print(f"PRIOR={P:<4} DIFF={D:<4}", fmt(r))
