# Extract crossing tau* per replicate for each fraction; also curve levels at fixed tau
import numpy as np, glob

def crossings(taus, C, S):
    out = []
    for c, s in zip(C, S):
        ok = ~np.isnan(c) & ~np.isnan(s)
        t = taus[ok]; g = c[ok] - s[ok]  # taus descending
        # first sign change from + to - scanning high->low tau
        x = np.nan
        for k in range(len(g) - 1):
            if g[k] > 0 and g[k + 1] <= 0:
                x = t[k] + (t[k + 1] - t[k]) * (g[k] / (g[k] - g[k + 1]))
                break
        out.append(x)
    return np.array(out)

def level_at(taus, A, tau0):
    i = np.argmin(np.abs(taus - tau0))
    col = A[:, i]
    # if NaN at exact checkpoint, find nearest non-nan column
    if np.isnan(col).all():
        valid = np.where(~np.isnan(A).all(axis=0))[0]
        i = valid[np.argmin(np.abs(taus[valid] - tau0))]
        col = A[:, i]
    return np.nanmean(col), np.nanstd(col), taus[i]

print(f"{'frac':>5} {'n':>5} {'reps':>4} {'tau* mean':>9} {'sd':>6} | Phi_att@0.85 | Phi_coh@0.85 | Phi_att@0.828")
rows = []
for f in sorted(glob.glob('data/experiments/review/cohdiv_frac_*.npz')):
    d = np.load(f)
    taus, C, S = d['taus'], d['C'], d['S']
    n = int(d['ns'][0]); frac = float(d['frac'])
    cr = crossings(taus, C, S)
    cr = cr[~np.isnan(cr)]
    a85, a85sd, _ = level_at(taus, S, 0.85)
    c85, c85sd, _ = level_at(taus, C, 0.85)
    a828, a828sd, _ = level_at(taus, S, 0.828)
    rows.append((frac, n, len(cr), cr.mean(), cr.std(), a85, a85sd, c85, c85sd, a828, a828sd))
rows.sort()
for r in rows:
    print(f"{r[0]:5.2f} {r[1]:5d} {r[2]:4d} {r[3]:9.4f} {r[4]:6.4f} | {r[5]:.4f}+-{r[6]:.4f} | {r[7]:.4f}+-{r[8]:.4f} | {r[9]:.4f}+-{r[10]:.4f}")

# sanity: existing 100-rep 80% results
try:
    d = np.load('data/experiments/review/cohdiv_all.npz')
    if 'cross' in d:
        cr = d['cross']; cr = cr[~np.isnan(cr)]
        print(f"\nexisting cohdiv_all (80%, 100 reps): cross mean {cr.mean():.4f} sd {cr.std():.4f}")
    else:
        cr = crossings(d['taus'], d['C'], d['S']); cr = cr[~np.isnan(cr)]
        print(f"\nexisting cohdiv_all recomputed: mean {cr.mean():.4f} sd {cr.std():.4f}")
except Exception as e:
    print('cohdiv_all check failed:', e)

# log-linear trend fit: tau* vs log(n)
import numpy as np
ns = np.array([r[1] for r in rows]); ts = np.array([r[3] for r in rows])
b, a = np.polyfit(np.log(ns), ts, 1)
print(f"\nfit tau* = {a:.4f} + {b:.5f} * ln(n)  -> per-doubling shift {b*np.log(2):+.5f}")
print(f"extrapolation: n=10000 -> tau* ~ {a + b*np.log(10000):.4f} ; n=100000 -> {a + b*np.log(100000):.4f}")
