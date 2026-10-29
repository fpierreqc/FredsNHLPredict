#!/usr/bin/env python3
"""
elo_fred.py — Équation Fred, colonne vertébrale Elo pour Bendevine.ca (LNH).

Règles (version du 28 octobre 2026) :
  K = 8, domicile +25, marge de victoire 1 + 0,5·ln(écart), prolongation/TB ×0,75
  substitut devant le filet : −30 ; deuxième match en deux soirs : −30
  match « tranché » : |p − 0,5| > 0,08 ; pointage indicatif : 3-2 dans le sens du gagnant

Usage :
  python3 elo_fred.py backtest data/games_2026-27.csv        # rejoue la saison, imprime le bilan
  python3 elo_fred.py predict MTL TOR --home-sub --away-b2b   # probabilité d'un match
  python3 elo_fred.py update MTL TOR 3 2 --ot                 # met à jour elo_current.json après un match
"""
import json, math, csv, sys, argparse
from collections import defaultdict

PARAMS = dict(K=8, HOME=25, MOV=0.5, BACKUP=30, B2B=30, OT_MULT=0.75)
CONF = 0.08
STATE = "elo_current.json"

def norm(t): return "VEG" if t == "VGK" else t

class EloFred:
    def __init__(self, ratings=None, params=None):
        self.p = dict(PARAMS, **(params or {}))
        self.r = defaultdict(lambda: 1500.0)
        if ratings: self.r.update({norm(k): float(v) for k, v in ratings.items()})

    @classmethod
    def load(cls, path=STATE):
        d = json.load(open(path)); return cls(d.get("ratings"), d.get("params"))

    def save(self, path=STATE, **meta):
        json.dump(dict(params=self.p, **meta, ratings={t: round(v, 1) for t, v in sorted(self.r.items(), key=lambda x: -x[1])}),
                  open(path, "w"), indent=1)

    def prob_home(self, home, away, home_sub=0, away_sub=0, home_b2b=0, away_b2b=0):
        home, away = norm(home), norm(away)
        adj = self.p["HOME"] + self.p["BACKUP"] * (away_sub - home_sub) + self.p["B2B"] * (away_b2b - home_b2b)
        return 1 / (1 + 10 ** (-(self.r[home] - self.r[away] + adj) / 400))

    def predict(self, home, away, **kw):
        ph = self.prob_home(home, away, **kw)
        pick = home if ph >= .5 else away
        return dict(home=home, away=away, p_home=round(ph, 3), pick=pick, confident=abs(ph - .5) > CONF,
                    score=f"{pick} 3-2")

    def update(self, home, away, hg, ag, ot=False, ph=None, **kw):
        home, away = norm(home), norm(away)
        if ph is None: ph = self.prob_home(home, away, **kw)
        s = 1 if hg > ag else 0
        m = 1 + self.p["MOV"] * math.log(max(abs(hg - ag), 1))
        if ot: m *= self.p["OT_MULT"]
        d = self.p["K"] * m * (s - ph); self.r[home] += d; self.r[away] -= d
        return d

def backtest(path, start=None):
    m = EloFred.load(start) if start else EloFred()
    last = {}; n = ok = cf = cok = ex = 0; ll = 0
    for g in csv.DictReader(open(path)):
        h, a = g["home"], g["away"]; hg, ag = int(g["home_goals"]), int(g["away_goals"]); ot = g["ot"] == "1"
        kw = dict(home_sub=int(g["home_sub"]), away_sub=int(g["away_sub"]),
                  home_b2b=int(last.get(h) == prev(g["date"])), away_b2b=int(last.get(a) == prev(g["date"])))
        pr = m.predict(h, a, **kw); won = h if hg > ag else a
        n += 1; ok += pr["pick"] == won; cf += pr["confident"]; cok += pr["confident"] and pr["pick"] == won
        ex += (hg, ag) == ((3, 2) if pr["pick"] == h else (2, 3)); ll += -math.log(pr["p_home"] if hg > ag else 1 - pr["p_home"])
        m.update(h, a, hg, ag, ot, ph=pr["p_home"]); last[h] = last[a] = g["date"]
    print(f"{n} matchs : {ok} bons ({ok/n:.1%}) | tranchés {cok}/{cf} ({cok/max(cf,1):.1%}) | pointage exact {ex} ({ex/n:.1%}) | logloss {ll/n:.4f}")
    return m

def prev(d):
    import datetime; return (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("backtest"); b.add_argument("csv"); b.add_argument("--start")
    p = sub.add_parser("predict"); p.add_argument("home"); p.add_argument("away")
    for f in ("home-sub", "away-sub", "home-b2b", "away-b2b"): p.add_argument("--" + f, action="store_true")
    u = sub.add_parser("update"); u.add_argument("home"); u.add_argument("away"); u.add_argument("hg", type=int); u.add_argument("ag", type=int)
    u.add_argument("--ot", action="store_true")
    for f in ("home-sub", "away-sub", "home-b2b", "away-b2b"): u.add_argument("--" + f, action="store_true")
    a = ap.parse_args()
    if a.cmd == "backtest": backtest(a.csv, a.start)
    elif a.cmd == "predict":
        print(EloFred.load().predict(a.home, a.away, home_sub=a.home_sub, away_sub=a.away_sub, home_b2b=a.home_b2b, away_b2b=a.away_b2b))
    elif a.cmd == "update":
        m = EloFred.load(); d = m.update(a.home, a.away, a.hg, a.ag, a.ot, home_sub=a.home_sub, away_sub=a.away_sub, home_b2b=a.home_b2b, away_b2b=a.away_b2b)
        m.save(season="2026-27"); print(f"Δ {d:+.1f} → {a.home} {m.r[norm(a.home)]:.0f}, {a.away} {m.r[norm(a.away)]:.0f}")
    else: ap.print_help()
