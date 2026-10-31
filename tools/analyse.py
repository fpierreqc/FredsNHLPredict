#!/usr/bin/env python3
"""Rejoue la saison, imprime les prédictions à partir d'une date, et teste des variantes de paramètres.
Usage : python3 tools/analyse.py [--from 2026-10-28] [--variants]"""
import sys, csv, math, json, argparse, datetime
sys.path.insert(0, ".")
from elo_fred import EloFred, CONF

def load(path): return list(csv.DictReader(open(path)))
def prev(d): return (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()

def replay(games, start_json, params=None, show_from=None, score=lambda pick_home: (3,2), eval_from=None, rest_bonus=0):
    m = EloFred(json.load(open(start_json))["ratings"], params)
    last = {}; st = dict(n=0, ok=0, cf=0, cok=0, ex=0, ll=0.0); rows = []
    for g in games:
        d, h, a = g["date"], g["home"], g["away"]; hg, ag = int(g["home_goals"]), int(g["away_goals"]); ot = g["ot"] == "1"
        hb2, ab2 = int(last.get(h) == prev(d)), int(last.get(a) == prev(d))
        kw = dict(home_sub=int(g["home_sub"]), away_sub=int(g["away_sub"]), home_b2b=hb2, away_b2b=ab2)
        ph = m.prob_home(h, a, **kw)
        if rest_bonus:
            def rest(t):
                if t not in last: return 0
                return (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(last[t])).days
            rh, ra = rest(h), rest(a); adj = rest_bonus * ((rh >= 3) - (ra >= 3))
            ph = 1 / (1 + 10 ** (-(math.log10(ph / (1 - ph)) * 400 + adj) / 400))
        pick = h if ph >= .5 else a; conf = abs(ph - .5) > CONF; won = h if hg > ag else a
        sc = score(pick == h); exact = (hg, ag) == (sc if pick == h else sc[::-1])
        if eval_from is None or d >= eval_from:
            st["n"] += 1; st["ok"] += pick == won; st["cf"] += conf; st["cok"] += conf and pick == won; st["ex"] += exact
            st["ll"] += -math.log(ph if hg > ag else 1 - ph)
        if show_from and d >= show_from:
            rows.append((d, a, h, g["away_sub"], g["home_sub"], ab2, hb2, pick, max(ph, 1-ph), conf, ag, hg, ot, pick == won, exact))
        m.update(h, a, hg, ag, ot, ph=ph); last[h] = last[a] = d
    return st, rows, m

def fmt(st): return f"{st['ok']}/{st['n']} ({st['ok']/st['n']:.1%}) | tranchés {st['cok']}/{st['cf']} ({st['cok']/max(st['cf'],1):.1%}) | exact {st['ex']} | logloss {st['ll']/st['n']:.4f}"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="frm"); ap.add_argument("--variants", action="store_true")
    ap.add_argument("--csv", default="data/games_2026-27.csv"); ap.add_argument("--start", default="data/elo_start_2026-27.json")
    a = ap.parse_args(); G = load(a.csv)
    st, rows, m = replay(G, a.start, show_from=a.frm)
    for r in rows:
        d, aw, h, asb, hsb, ab2, hb2, pick, p, conf, ag, hg, ot, ok, ex = r
        tag = lambda s, b: (" S" if s == "1" else "") + (" B2B" if b else "")
        print(f"{d} {aw}{tag(asb,ab2)} @ {h}{tag(hsb,hb2)} → {pick} {p:.0%}{' T' if conf else ''} | réel {ag}-{hg}{' P' if ot else ''} {'OK' if ok else 'X'}{' EXACT' if ex else ''}")
    if rows:
        sub = dict(n=len(rows), ok=sum(r[13] for r in rows), cf=sum(r[9] for r in rows), cok=sum(r[9] and r[13] for r in rows), ex=sum(r[14] for r in rows), ll=0)
        print(f"Période : {sub['ok']}/{sub['n']} | tranchés {sub['cok']}/{sub['cf']} | exact {sub['ex']}")
    print("Saison :", fmt(st))
    if a.variants:
        print("--- variantes (saison complète) ---")
        for nm, p in [("actuel", {}), ("K6", dict(K=6)), ("K10", dict(K=10)), ("HOME40", dict(HOME=40)), ("HOME50", dict(HOME=50)),
                      ("B2B0", dict(B2B=0)), ("B2B45", dict(B2B=45)), ("BACKUP0", dict(BACKUP=0)), ("BACKUP45", dict(BACKUP=45)), ("MOV0", dict(MOV=0)), ("MOV1", dict(MOV=1.0))]:
            s, _, _ = replay(G, a.start, p); print(f"{nm:9s}", fmt(s))
        for rb in (15, 30): s, _, _ = replay(G, a.start, rest_bonus=rb); print(f"repos+{rb:<3}", fmt(s))
        mid = G[len(G)//2]["date"]
        print(f"--- hors échantillon (évalué à partir de {mid}) ---")
        for nm, p in [("actuel", {}), ("HOME50", dict(HOME=50)), ("B2B0", dict(B2B=0)), ("BACKUP45", dict(BACKUP=45))]:
            s, _, _ = replay(G, a.start, p, eval_from=mid); print(f"{nm:9s}", fmt(s))
        for rb in (15, 30): s, _, _ = replay(G, a.start, rest_bonus=rb, eval_from=mid); print(f"repos+{rb:<3}", fmt(s))
        from collections import Counter
        print("pointages:", Counter(tuple(sorted((int(g['home_goals']), int(g['away_goals'])), reverse=True)) for g in G).most_common(6))
        print("domicile:", f"{sum(int(g['home_goals'])>int(g['away_goals']) for g in G)/len(G):.1%}")
