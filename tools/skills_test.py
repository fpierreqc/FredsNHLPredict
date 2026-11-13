#!/usr/bin/env python3
"""Tests inspirés des skills PuckAPI (elo-engineering, probability-calibration, totals-modeling).
Tout est « walk-forward » : chaque prédiction n'utilise que les matchs antérieurs.
Usage : python3 tools/skills_test.py"""
import sys, json, math, datetime
from collections import defaultdict, deque
sys.path.insert(0, ".")
from elo_fred import EloFred, CONF
from tools.analyse import load, prev

G = load("data/games_2026-27.csv"); START = json.load(open("data/elo_start_2026-27.json"))["ratings"]
logit = lambda p: math.log(p / (1 - p)); sig = lambda x: 1 / (1 + math.exp(-x))

def summarize(P, Y, lab):
    n = len(P); ok = sum((p >= .5) == y for p, y in zip(P, Y)); T = [(p, y) for p, y in zip(P, Y) if abs(p - .5) > CONF]
    tok = sum((p >= .5) == y for p, y in T); ll = -sum(math.log(p if y else 1 - p) for p, y in zip(P, Y)) / n
    br = sum((p - y) ** 2 for p, y in zip(P, Y)) / n
    print(f"{lab:26s} {ok}/{n} ({ok/n:.1%}) | tranchés {tok}/{len(T)} ({tok/max(len(T),1):.1%}) | logloss {ll:.4f} | Brier {br:.4f}")
    return ll

def run(params=None, mov="fred", form_n=0, form_w=0.0, fade=0.0, start=START, eval_from=None):
    """Rejoue la saison. mov: fred | skill (ln(d+1)*2.2/(0.001*écart+2.2), plafond 1,8) | flat. form: bonus Elo de forme."""
    m = EloFred(start, params); last = {}; hist = defaultdict(lambda: deque(maxlen=max(form_n, 1))); P = []; Y = []; rows = []
    for g in G:
        d, h, a = g["date"], g["home"], g["away"]; hg, ag = int(g["home_goals"]), int(g["away_goals"]); ot = g["ot"] == "1"
        kw = dict(home_sub=int(g["home_sub"]), away_sub=int(g["away_sub"]), home_b2b=int(last.get(h) == prev(d)), away_b2b=int(last.get(a) == prev(d)))
        ph0 = m.prob_home(h, a, **kw); ph = ph0
        if form_n:
            f = sum(hist[h]) - sum(hist[a])                      # surperformance récente (victoires − attendu)
            ph = 1 / (1 + 10 ** (-(400 * math.log10(ph0 / (1 - ph0)) + form_w * f) / 400))
        y = hg > ag
        if eval_from is None or d >= eval_from: P.append(ph); Y.append(y)
        rows.append((d, ph, y))
        s = 1 if y else 0; K = m.p["K"]
        if mov == "fred": mult = 1 + m.p["MOV"] * math.log(max(abs(hg - ag), 1))
        elif mov == "skill":
            wd = (m.r[h] - m.r[a]) if y else (m.r[a] - m.r[h]); mult = min(math.log(abs(hg - ag) + 1) * 2.2 / (wd * 0.001 + 2.2), 1.8)
        else: mult = 1.0
        if ot: mult *= m.p["OT_MULT"]
        delta = K * mult * (s - ph0); m.r[h] += delta; m.r[a] -= delta
        if form_n: hist[h].append(s - ph0); hist[a].append((1 - s) - (1 - ph0))
        last[h] = last[a] = d
    return P, Y, rows, m

print("=== 1. ELO-ENGINEERING : variantes ===")
P, Y, rows, _ = run(); base_ll = summarize(P, Y, "Équation Fred actuelle")
summarize(*run(dict(K=10, HOME=35), mov="skill")[:2], "Skill : K10 dom35 MOV skill")
summarize(*run(mov="skill")[:2], "MOV skill (K8 dom25)")
summarize(*run(dict(K=10))[:2], "K10 (MOV Fred)")
summarize(*run(dict(HOME=35))[:2], "Domicile 35")
summarize(*run(dict(K=15), mov="flat")[:2], "Flat-K 15 (sans MOV)")
for n in (5, 7, 10):
    for w in (20, 40, 60):
        summarize(*run(form_n=n, form_w=w)[:2], f"Forme N={n} poids {w}")
mid = G[len(G) // 2]["date"]
print(f"--- hors échantillon (à partir de {mid}) ---")
summarize(*run(eval_from=mid)[:2], "actuelle")
summarize(*run(dict(K=10, HOME=35), mov="skill", eval_from=mid)[:2], "K10 dom35 MOV skill")
summarize(*run(mov="skill", eval_from=mid)[:2], "MOV skill")
for n, w in ((5, 40), (7, 40), (10, 40), (10, 60)):
    summarize(*run(form_n=n, form_w=w, eval_from=mid)[:2], f"Forme N={n} poids {w}")

print("\n=== 2. PROBABILITY-CALIBRATION ===")
fav = [(max(p, 1 - p), (p >= .5) == y) for p, y in zip(P, Y)]
print("Courbe de fiabilité (cote du favori) :")
for lo, hi in ((.50, .54), (.54, .58), (.58, .62), (.62, .66), (.66, .70), (.70, 1.0)):
    s = [(p, w) for p, w in fav if lo <= p < hi]
    if s: print(f"  {lo:.2f}-{hi:.2f} : n={len(s):3d} prédit {sum(p for p,_ in s)/len(s):.1%} réel {sum(w for _,w in s)/len(s):.1%}")
n = len(P); br = sum((p - y) ** 2 for p, y in zip(P, Y)) / n; base = sum(Y) / n
print(f"Brier {br:.4f} | constante {base*(1-base):.4f} | pile ou face 0.2500 | erreur moy. de calibration {sum(abs(sum(p for p,_ in s)/len(s) - sum(w for _,w in s)/len(s))*len(s) for s in [[(p,w) for p,w in fav if lo<=p<hi] for lo,hi in ((.50,.54),(.54,.58),(.58,.62),(.62,.66),(.66,.70),(.70,1.0))] if s)/n:.1%}")
# Platt walk-forward : on ajuste logit(p_cal) = a + b·logit(p) sur les matchs passés (min 150), on applique au suivant
def platt_fit(ps, ys, it=200, lr=0.5):
    a, b = 0.0, 1.0
    for _ in range(it):
        ga = gb = 0.0
        for p, y in zip(ps, ys):
            q = sig(a + b * logit(p)); ga += q - y; gb += (q - y) * logit(p)
        a -= lr * ga / len(ps); b -= lr * gb / len(ps)
    return a, b
raw = []; cal = []; yy = []
for i in range(150, n):
    if (i - 150) % 15 == 0: a, b = platt_fit(P[:i], Y[:i])
    raw.append(P[i]); cal.append(sig(a + b * logit(P[i]))); yy.append(Y[i])
print(f"Platt (dernier ajustement a={a:+.3f}, b={b:.2f} ; b>1 = modèle trop timide, b<1 = trop confiant)")
summarize(raw, yy, "  brut (matchs 151+)"); summarize(cal, yy, "  après Platt")

print("\n=== 3. TOTALS-MODELING : buts ===")
# Component Elo attaque/défense en buts + effets de contexte (B2B, substitut, début de saison)
def totals(Kc=0.03, home_adv=0.15, use_ctx=True, prior=3.05):
    off = defaultdict(float); de = defaultdict(float); last = {}; lg = [prior * 2] * 30; out = []; gp = defaultdict(int)
    for g in G:
        d, h, a = g["date"], g["home"], g["away"]; hg, ag = int(g["home_goals"]), int(g["away_goals"])
        mu = sum(lg[-200:]) / len(lg[-200:]) / 2
        hb, ab = int(last.get(h) == prev(d)), int(last.get(a) == prev(d)); hs, as_ = int(g["home_sub"]), int(g["away_sub"])
        eh = mu + off[h] - de[a] + home_adv; ea = mu + off[a] - de[h] - home_adv
        if use_ctx: eh += 0.15 * ab + 0.15 * as_; ea += 0.15 * hb + 0.15 * hs
        out.append(dict(d=d, eh=eh, ea=ea, hg=hg, ag=ag, n=min(gp[h], gp[a]), ctx=hb + ab + hs + as_))
        # buts en prolongation : on plafonne l'écart de mise à jour pour ne pas surpondérer les explosions
        rh, ra = max(min(hg - eh, 3), -3), max(min(ag - ea, 3), -3)
        off[h] += Kc * rh; de[a] -= Kc * rh; off[a] += Kc * ra; de[h] -= Kc * ra
        lg.append(hg + ag); last[h] = last[a] = d; gp[h] += 1; gp[a] += 1
    return out
def evalt(out, lab, min_n=8):
    S = [o for o in out if o["n"] >= min_n]; n = len(S)
    tot = [o["hg"] + o["ag"] for o in S]; pt = [o["eh"] + o["ea"] for o in S]; mt = sum(tot) / n
    rmse = math.sqrt(sum((p - t) ** 2 for p, t in zip(pt, tot)) / n); rm0 = math.sqrt(sum((mt - t) ** 2 for t in tot) / n)
    mx, my = sum(pt) / n, mt; cov = sum((x - mx) * (y - my) for x, y in zip(pt, tot)); vx = sum((x - mx) ** 2 for x in pt); vy = sum((y - my) ** 2 for y in tot)
    corr = cov / math.sqrt(vx * vy) if vx > 0 else 0
    print(f"{lab:34s} n={n} | RMSE total {rmse:.3f} (constante {rm0:.3f}) | corrélation {corr:+.3f}")
    return corr
for Kc in (0.02, 0.04, 0.08):
    evalt(totals(Kc=Kc, use_ctx=False), f"Component Elo Kc={Kc} sans contexte")
evalt(totals(Kc=0.04, use_ctx=True), "Component Elo Kc=0.04 + contexte")
out = totals(Kc=0.04, use_ctx=False)
ctx = [o["hg"] + o["ag"] for o in out if o["ctx"] > 0]; noc = [o["hg"] + o["ag"] for o in out if o["ctx"] == 0]
print(f"Total moyen : avec B2B/substitut {sum(ctx)/len(ctx):.2f} (n={len(ctx)}) vs sans {sum(noc)/len(noc):.2f} (n={len(noc)})")
early = [int(g["home_goals"]) + int(g["away_goals"]) for g in G[:len(G)//2]]; late = [int(g["home_goals"]) + int(g["away_goals"]) for g in G[len(G)//2:]]
print(f"Total moyen : 1re moitié {sum(early)/len(early):.2f} vs 2e moitié {sum(late)/len(late):.2f}")
# écart : l'Elo prédit-il la marge ?
import statistics
mg = [(abs(p - .5), abs(int(g["home_goals"]) - int(g["away_goals"])), ((p >= .5) == (int(g["home_goals"]) > int(g["away_goals"])))) for p, g in zip(P, G)]
for lo, hi in ((0, .04), (.04, .08), (.08, .14), (.14, .5)):
    s = [x for x in mg if lo <= x[0] < hi]; w = [x for x in s if x[2]]
    print(f"  cote {0.5+lo:.2f}-{0.5+hi:.2f} : n={len(s)} | favori gagne par 2+ : {sum(x[1] >= 2 for x in w)/len(s):.0%} | marge moy. quand il gagne {statistics.mean(x[1] for x in w):.2f}")
