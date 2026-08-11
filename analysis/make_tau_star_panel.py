# Summary CSV + supplementary panel: tau*(n)
import numpy as np, glob, csv

def crossings(taus, C, S):
    out = []
    for c, s in zip(C, S):
        ok = ~np.isnan(c) & ~np.isnan(s)
        t = taus[ok]; g = c[ok] - s[ok]
        x = np.nan
        for k in range(len(g) - 1):
            if g[k] > 0 and g[k + 1] <= 0:
                x = t[k] + (t[k + 1] - t[k]) * (g[k] / (g[k] - g[k + 1]))
                break
        out.append(x)
    return np.array(out)

rows = []
for f in sorted(glob.glob('data/experiments/review/cohdiv_frac_*.npz')):
    d = np.load(f)
    cr = crossings(d['taus'], d['C'], d['S']); cr = cr[~np.isnan(cr)]
    rows.append((float(d['frac']), int(d['ns'][0]), len(cr), cr.mean(), cr.std()))
rows.sort()
with open('data/experiments/review/tau_star_vs_n.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['fraction', 'n', 'n_reps', 'tau_star_mean', 'tau_star_sd'])
    for r in rows: w.writerow([f"{r[0]:.2f}", r[1], r[2], f"{r[3]:.4f}", f"{r[4]:.4f}"])
print('wrote tau_star_vs_n.csv')

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    ns = np.array([r[1] for r in rows]); ts = np.array([r[3] for r in rows]); sd = np.array([r[4] for r in rows])
    b, a = np.polyfit(np.log(ns), ts, 1)
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.errorbar(ns, ts, yerr=2 * sd, fmt='o', ms=5, capsize=3, color='#1a6b8a', label=r'$\tau^*(n)$ (mean $\pm$ 2 s.d., 20 reps)')
    xs = np.linspace(ns.min() * 0.9, ns.max() * 1.05, 200)
    ax.plot(xs, a + b * np.log(xs), '--', color='#888', lw=1,
            label=fr'$\tau^* \approx {a:.3f} + {b:.3f}\,\ln n$')
    ax.axhline(0.828, color='goldenrod', lw=0.8, ls=':')
    ax.text(ns.min(), 0.8295, 'reported $\\tau^*$ (80% subsamples)', fontsize=7, color='goldenrod')
    ax.set_xscale('log')
    ax.set_xlabel('subsample size $n$ (log scale)')
    ax.set_ylabel(r'crossing $\tau^*$')
    ax.set_title(r'Cohesion–attraction crossing $\tau^*$ increases with inventory size', fontsize=9)
    ax.legend(fontsize=7, loc='lower right')
    fig.tight_layout()
    fig.savefig('data/experiments/review/tau_star_vs_n_panel.pdf')
    fig.savefig('data/experiments/review/tau_star_vs_n_panel.png', dpi=200)
    print('wrote panel pdf/png')
except ImportError:
    print('matplotlib unavailable; csv only')
