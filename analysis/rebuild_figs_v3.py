"""Rebuild paper_tau_percolation figures under the new architecture.

Flagship fig1 (3-panel), support fig2 (F4 merge anatomy), support fig5
(percolation context + per-step quality), appendix fig3 (standalone crossing)
and fig4 (tau*(n) scaling).  Nature style: DejaVu Sans 7 pt, 0.6 pt axes,
no top/right spines, fonttype 42, 400 dpi, grey-only background shading.
Reference lines are MEASURED quantities: tau1 = 0.818, tau2 = 0.690,
F1 (tau* = 0.8329, n = 1,383), F4 (tau* = 0.7753, n = 901).
"""
import json, colorsys, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 7,
    'axes.linewidth': 0.6, 'pdf.fonttype': 42,
    'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.direction': 'out', 'ytick.direction': 'out',
    'savefig.dpi': 400,
})
MM = 1/25.4
GREEN = '#1f6f5c'; ORANGE = '#c1550c'; PURPLE = '#7a4b8f'
BLUE = '#2e7bb5'; RED = '#b0332a'; GREY = '#888888'

TAU1, TAU2 = 0.818, 0.690           # measured transition means (t1s/t2s)
FLOW = json.load(open('data/experiments/review/flow_states.json'))['steps']
F1_TAU, F1_N = FLOW[0]['tau'], FLOW[0]['n_after']    # 0.8329, 1383
F4_TAU, F4_N = FLOW[3]['tau'], FLOW[3]['n_after']    # 0.7753, 901


def stable_slice(taus, sd):
    """First index where sd of pooled cohesion < 0.02 for 50 consecutive pts."""
    flat = sd[:, 0] < 0.02
    run, cut = 0, len(taus)
    for i, f in enumerate(flat):
        run = run + 1 if f else 0
        if run >= 50:
            cut = i - 49
            break
    return slice(cut, len(taus))


def flow_tier_markers(ax, y_txt=1.045):
    """Downward triangles on the top axis at the F1/F4 flow-tier thresholds."""
    for x, lab in [(F1_TAU, 'F1'), (F4_TAU, 'F4')]:
        ax.plot([x], [1.0], marker='v', ms=3.2, color='0.25', mec='0.25',
                transform=ax.get_xaxis_transform(), clip_on=False, zorder=6)
        ax.text(x, y_txt, lab, transform=ax.get_xaxis_transform(),
                ha='center', va='bottom', fontsize=6.5, color='0.25')


def panel_letter(ax, letter, x=-0.145):
    ax.text(x, 1.02, letter, transform=ax.transAxes, fontsize=11,
            fontweight='bold', va='bottom', ha='left')


def draw_crossing_panel(ax, d):
    """Cohesion-attraction crossing (shared by fig1 panel b and fig3)."""
    taus, C, tck, Sck, cross = d['taus'], d['C'], d['tck'], d['Sck'], d['cross']
    cm, cs = np.nanmean(C, 0), np.nanstd(C, 0)
    sm, ss = np.nanmean(Sck, 0), np.nanstd(Sck, 0)
    mu, sdv = cross.mean(), cross.std()
    ax.axvspan(mu - 2*sdv, mu + 2*sdv, color='0.88', lw=0, zorder=0)
    ax.axvline(mu, color='0.35', ls=':', lw=0.8)
    m = taus >= 0.60
    ax.fill_between(taus[m], (cm-2*cs)[m], (cm+2*cs)[m], color=GREEN,
                    alpha=0.15, lw=0)
    ax.plot(taus[m], cm[m], color=GREEN, lw=1.1,
            label=r'Within-cluster cohesion $\Phi_{\mathrm{coh}}$')
    mk = tck >= 0.60
    ax.fill_between(tck[mk], (sm-2*ss)[mk], (sm+2*ss)[mk], color=RED,
                    alpha=0.15, lw=0)
    ax.plot(tck[mk], sm[mk], color=RED, lw=1.1,
            label=r'Between-cluster attraction $\Phi_{\mathrm{att}}$')
    ycross = float(np.interp(mu, taus[::-1], cm[::-1]))
    ax.annotate(r'$\tau^{*}$ = 0.828 ± 0.004', xy=(mu, ycross),
                xytext=(0.800, 0.848), fontsize=6.5, color='0.2',
                arrowprops=dict(arrowstyle='-', lw=0.6, color='0.3'))
    flow_tier_markers(ax)
    ax.set_xlim(taus.max(), 0.60)
    ax.set_ylim(0.55, 0.965)
    ax.set_xlabel(r'Merge threshold $\tau$')
    ax.set_ylabel('Cosine similarity')
    ax.legend(frameon=False, loc='upper right', bbox_to_anchor=(0.995, 1.02), fontsize=6.5,
              handlelength=1.6, borderaxespad=0.25)
    return mu, sdv


# ---------------- Figure 1 (flagship, 3 panels) ----------------
def fig1():
    b = np.load('data/experiments/review/boot1000_agg.npz')
    taus, mean, sd = b['taus'], b['mean'], b['sd']
    t1s, t2s = b['t1s'], b['t2s']
    sl = stable_slice(taus, sd)
    t = taus[sl]

    fig = plt.figure(figsize=(120*MM, 160*MM))
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1.12, 1], hspace=0.52,
                          left=0.125, right=0.875, top=0.955, bottom=0.06)
    ax0 = fig.add_subplot(gs[0])
    axa = fig.add_subplot(gs[1])
    axb = fig.add_subplot(gs[2])

    # ---- panel a: connectivity (cluster counts / sizes) ----
    ax0.plot(t, np.maximum(mean[sl, 2]/0.8, 1), color=GREY, lw=1.0,
             label='Number of clusters')
    ax0.plot(t, np.maximum(mean[sl, 3]/0.8, 1), color=PURPLE, lw=1.0,
             label='Largest cluster')
    ax0.plot(t, np.maximum(mean[sl, 4]/0.8, 1), color=BLUE, lw=1.0,
             label='2nd-largest cluster')
    for x, lab in [(TAU1, r'$\tau_1$ = 0.818'), (TAU2, r'$\tau_2$ = 0.690')]:
        ax0.axvline(x, color='0.3', ls=':', lw=0.8)
        ax0.text(x - 0.004, 0.13, lab, transform=ax0.get_xaxis_transform(),
                 ha='left', va='bottom', fontsize=6.5, color='0.2')
    flow_tier_markers(ax0)
    ax0.set_yscale('log')
    ax0.set_xlim(0.905, 0.495)
    ax0.set_ylabel('Count or size (log scale)')
    ax0.set_xlabel(r'Merge threshold $\tau$')
    ax0.legend(frameon=False, loc='center right',
               bbox_to_anchor=(0.99, 0.60), fontsize=6.5)

    # ---- panel b: cohesion vs tau ----
    for arr in (t1s, t2s):                       # 95% subsample intervals
        lo, hi = np.percentile(arr, [2.5, 97.5])
        axa.axvspan(lo, hi, color='0.90', zorder=0, lw=0)
    for k, c, lab in [(0, GREEN, 'Pooled mean pairwise similarity'),
                      (1, ORANGE, 'Per-cluster minimum (mean)')]:
        lo = np.clip(mean[sl, k] - 2*sd[sl, k], 0, 1)
        hi = np.clip(mean[sl, k] + 2*sd[sl, k], 0, 1)
        axa.fill_between(t, lo, hi, color=c, alpha=0.18, lw=0)
        axa.plot(t, mean[sl, k], color=c, lw=1.1, label=lab)
    axa.axhline(0.570, color=GREY, ls='--', lw=0.9,
                label='Random-merge baseline')
    for x, lab, ty in [(TAU1, r'$\tau_1$ = 0.818', 0.955), (TAU2, r'$\tau_2$ = 0.690', 0.50)]:
        axa.axvline(x, color='0.3', ls=':', lw=0.8)
        axa.text(x - 0.004, ty, lab, ha='left', va='top', fontsize=6.5,
                 color='0.2')
    flow_tier_markers(axa)
    axa.set_xlim(0.905, 0.495)
    axa.set_ylim(0.28, 1.0)
    axa.set_xlabel(r'Merge threshold $\tau$')
    axa.set_ylabel('Within-cluster cohesion (cosine)')
    axa.legend(frameon=False, loc='upper right', bbox_to_anchor=(1.0, 0.97), fontsize=6.5, borderaxespad=0.0)

    # ---- panel b: cohesion-attraction crossing ----
    d = np.load('data/experiments/review/cohdiv_all.npz')
    draw_crossing_panel(axb, d)

    for ax, L in zip((ax0, axa, axb), 'abc'):
        panel_letter(ax, L)
    fig.savefig('data/experiments/review/tau_cohesion_nature_094.png')
    fig.savefig('paper_tau_percolation/fig1_tau_cohesion.pdf')
    plt.close(fig)


# ---------------- Figure 2 (support: F4 merge anatomy) ----------------
def fig2():
    master = json.load(open('data/experiments/stage1/out/master.json'))['cards']
    f4 = json.load(open('data/experiments/review/flow4_state.json'))['cards']
    emb = np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
    XY = np.load('data/experiments/review/fig2_xy.npz')['A']
    hier = json.load(open('public/data/releases/v2.18.0-rc/hierarchy.json'))['nodes']
    parent = {n['node_id']: n['parent_id'] for n in hier}
    assign = json.load(open('data/experiments/stage2/out/stage2_assignment.json'))['master']
    l3_of = {a['l4_id']: a['l3'] for a in assign}
    idx = {c['l4_id']: i for i, c in enumerate(master)}

    multi = [c for c in f4 if c['n'] >= 2]
    groups = [[idx[m] for m in c['members']] for c in multi]
    reps = [idx[c['rep']] for c in multi]
    gmin = np.array([c['min_cos'] for c in multi])
    sizes = np.array([c['n'] for c in multi])

    def fam(i):
        l3 = l3_of.get(master[i]['l4_id'])
        return parent.get(parent.get(l3))

    HUE = {'RAI1-G': 0.60, 'RAI1-A': 0.33, 'RAI1-P': 0.07}
    rng = np.random.default_rng(9)
    gcol, gfam = [], []
    for g in groups:
        fams = [fam(i) for i in g]
        maj = max(set(fams), key=fams.count) if fams else 'RAI1-G'
        h = HUE.get(maj, 0.60)
        s = 0.55 + 0.25*rng.random(); v = 0.55 + 0.3*rng.random()
        gcol.append(colorsys.hsv_to_rgb(h, s, v)); gfam.append(maj)
    in_group = set(i for g in groups for i in g)
    ung = [i for i in range(len(master)) if i not in in_group]

    fig = plt.figure(figsize=(183*MM, 162*MM))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.32,
                          wspace=0.27, left=0.06, right=0.975, top=0.95,
                          bottom=0.13)
    axa = fig.add_subplot(gs[0, 0]); axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0]); axd = fig.add_subplot(gs[1, 1])

    # panel a: master with F4 cumulative merge groups
    axa.scatter(XY[ung, 0], XY[ung, 1], s=2, c='0.82', lw=0, zorder=1)
    for g, r, col in zip(groups, reps, gcol):
        for i in g:
            if i != r:
                from matplotlib.patches import FancyArrowPatch
                axa.add_patch(FancyArrowPatch(
                    (XY[i, 0], XY[i, 1]), (XY[r, 0], XY[r, 1]),
                    connectionstyle='arc3,rad=0.22', arrowstyle='-',
                    color=col, lw=0.25, alpha=0.5, zorder=2))
        axa.scatter(XY[g, 0], XY[g, 1], s=4, color=[col], lw=0, zorder=3)
    axa.set_title('Master', fontsize=8)
    axa.text(0.5, -0.045,
             f'{len(groups)} cumulative merge groups · '
             f'{int(sizes.sum())} cards involved',
             transform=axa.transAxes, ha='center', fontsize=6.5, color='0.45')

    # panel b: F4 state, groups collapsed to representatives
    axb.scatter(XY[ung, 0], XY[ung, 1], s=2, c='0.82', lw=0, zorder=1)
    for g, r, col in zip(groups, reps, gcol):
        ghosts = [i for i in g if i != r]
        axb.scatter(XY[ghosts, 0], XY[ghosts, 1], s=1.5, c='0.92', lw=0,
                    zorder=0)
        axb.scatter(XY[r, 0], XY[r, 1], s=3 + 1.8*len(g), color=[col],
                    lw=0.4, edgecolor='white', zorder=3)
    axb.set_title('F4', fontsize=8)
    axb.text(0.5, -0.045, 'groups collapsed to representatives · 901 cards',
             transform=axb.transAxes, ha='center', fontsize=6.5, color='0.45')
    for a in (axa, axb):
        a.set_xticks([]); a.set_yticks([])
        a.spines[['left', 'bottom']].set_visible(False)

    # panel c: stacked histogram of group sizes by family (2..10, 11+)
    FAMS = ['RAI1-G', 'RAI1-A', 'RAI1-P']
    FNAME = {'RAI1-G': 'General', 'RAI1-A': 'Agentic', 'RAI1-P': 'Physical'}
    FCOL = {f: colorsys.hsv_to_rgb(HUE[f], 0.65, 0.75) for f in FAMS}
    xs = np.arange(2, 12)                       # 11 slot = '11+'
    binned = np.minimum(sizes, 11)
    bottom = np.zeros(len(xs))
    for f in FAMS:
        cnt = np.array([sum(1 for s0, fm in zip(binned, gfam)
                            if s0 == x and fm == f) for x in xs])
        axc.bar(xs, cnt, bottom=bottom, color=FCOL[f], width=0.75, lw=0)
        bottom += cnt
    for x, btot in zip(xs, bottom):
        if btot > 0:
            axc.text(x, btot + 2, str(int(btot)), ha='center', fontsize=6,
                     color='0.3')
    axc.set_xlabel('Merge-group size')
    axc.set_ylabel('Number of merge groups')
    axc.set_xticks(xs)
    axc.set_xticklabels([str(x) for x in xs[:-1]] + ['11+'])
    axc.set_ylim(0, bottom.max()*1.12)

    # panel d: min within-group cosine vs true size, with random-group null
    rng3 = np.random.default_rng(3)
    uniq = sorted(set(sizes))
    null_lo, null_hi, null_md = [], [], []
    for s0 in uniq:
        mins = []
        for _ in range(200):
            pick = rng3.choice(len(master), size=s0, replace=False)
            E = emb[pick]; S = E @ E.T
            mins.append(S[np.triu_indices(s0, 1)].min())
        null_lo.append(np.percentile(mins, 2.5))
        null_hi.append(np.percentile(mins, 97.5))
        null_md.append(np.median(mins))
    axd.fill_between(uniq, null_lo, null_hi, color='0.88', lw=0,
                     label='Random-group null (95%)')
    axd.plot(uniq, null_md, color='0.6', lw=0.7)
    jit = np.exp(rng3.normal(0, 0.022, len(sizes)))
    for f in FAMS:
        m = [i for i, fm in enumerate(gfam) if fm == f]
        axd.scatter(sizes[m]*jit[m], gmin[m], s=5, color=FCOL[f], lw=0,
                    alpha=0.85, zorder=3)
    axd.axhline(F4_TAU, color='0.3', ls='--', lw=0.8)
    axd.text(58, F4_TAU + 0.012, r'$\tau^{*}_{4}$ = 0.775', fontsize=6.5,
             ha='right', color='0.3')
    axd.set_xscale('log')
    axd.set_xlim(1.8, 62)
    axd.set_xticks([2, 3, 4, 5, 7, 10, 15, 20, 30, 50])
    axd.set_xticklabels(['2', '3', '4', '5', '7', '10', '15', '20', '30', '50'])
    axd.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    axd.set_xlabel('Merge-group size (log scale)')
    axd.set_ylabel('Minimum within-group cosine')

    for a, L in zip((axa, axb, axc, axd), 'abcd'):
        a.text(-0.05, 1.05, L, transform=a.transAxes, fontsize=11,
               fontweight='bold', va='top')
    handles = [plt.Line2D([], [], marker='o', ls='', ms=5, color=FCOL[f],
               label=FNAME[f]) for f in FAMS]
    handles.append(plt.Line2D([], [], marker='o', ls='', ms=5, color='0.82',
                   label='Unmerged'))
    fig.legend(handles=handles, loc='lower center', ncol=4, frameon=False,
               fontsize=7, bbox_to_anchor=(0.5, 0.015))
    fig.savefig('data/experiments/review/fig2_before_after.png')
    fig.savefig('paper_tau_percolation/fig2_before_after.pdf')
    plt.close(fig)


# ---------------- Figure 3 (appendix: standalone crossing) ----------------
def fig3():
    d = np.load('data/experiments/review/cohdiv_all.npz')
    fig, ax = plt.subplots(figsize=(120*MM, 80*MM))
    draw_crossing_panel(ax, d)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.90, bottom=0.135)
    fig.savefig('data/experiments/review/fig3_cohesion_attraction.png')
    fig.savefig('paper_tau_percolation/fig3_cohesion_attraction.pdf')
    plt.close(fig)


# ---------------- Figure 4 (appendix: tau*(n) scaling) ----------------
def crossing(taus, C, S):
    out = []
    for c, s in zip(C, S):
        dd = c - s
        ok = ~np.isnan(dd)
        t, dd = taus[ok], dd[ok]
        o = np.argsort(-t); t, dd = t[o], dd[o]
        for i in range(1, len(dd)):
            if dd[i-1] > 0 >= dd[i]:
                out.append(t[i-1] + (t[i]-t[i-1])*dd[i-1]/(dd[i-1]-dd[i]))
                break
    return np.array(out)


def fig4():
    rows = []
    for f in sorted(glob.glob('data/experiments/review/cohdiv_frac_*.npz')):
        d = np.load(f)
        cr = crossing(d['taus'], d['C'], d['S'])
        if len(cr):
            rows.append((float(np.mean(d['ns'])), cr.mean(), cr.std()))
    rows.sort()
    n = np.array([r[0] for r in rows]); m = np.array([r[1] for r in rows])
    s = np.array([r[2] for r in rows])
    fig, ax = plt.subplots(figsize=(88*MM, 66*MM))
    ax.errorbar(n, m, yerr=2*s, fmt='o', ms=3, color=GREEN, elinewidth=0.8,
                capsize=2, lw=0)
    a, b = np.polyfit(np.log(n), m, 1)
    xs = np.geomspace(n.min()*0.9, n.max()*1.1, 100)
    ax.plot(xs, a*np.log(xs) + b, ls='--', color='0.4', lw=0.9)
    ax.text(0.05, 0.9, rf'$\tau^*\approx{b:.3f}+{a:.4f}\,\ln n$',
            transform=ax.transAxes, fontsize=6.5, color='0.3')
    ax.axhline(0.828, color='goldenrod', ls=':', lw=0.9)
    ax.text(0.03, 0.8272, r'$\tau^*$ at 80% subsamples',
            transform=ax.get_yaxis_transform(), ha='left', va='top',
            fontsize=6, color='goldenrod')
    ax.set_xscale('log')
    ax.set_xlabel('Inventory size n (log scale)')
    ax.set_ylabel(r'Crossing threshold $\tau^{*}$')
    fig.tight_layout()
    fig.savefig('paper_tau_percolation/fig4_tau_star_vs_n.pdf')
    fig.savefig('data/experiments/review/tau_star_vs_n_panel.png')
    plt.close(fig)


# ---------------- Figure 5 (support: per-step quality, single panel) -----
def fig5():
    fig = plt.figure(figsize=(120*MM, 130*MM))
    gs = fig.add_gridspec(2, 1, hspace=0.42, left=0.125, right=0.865,
                          top=0.95, bottom=0.08)
    axa = fig.add_subplot(gs[0])
    axb = fig.add_subplot(gs[1])

    steps = np.arange(1, len(FLOW) + 1)
    tau_t = np.array([s['tau'] for s in FLOW])
    n_t = np.array([s['n_after'] for s in FLOW], float)
    med_min = np.array([s['med_min'] for s in FLOW])
    med_z = np.array([s['med_z'] for s in FLOW])

    # ---- panel a: granularity flow trajectory ----
    axa.axvspan(14.5, 28.5, color='0.92', zorder=0, lw=0)
    axa.text(21.5, 0.955, 'stepwise validity below threshold',
             transform=axa.get_xaxis_transform(), ha='center', va='top',
             fontsize=6, color='0.35')
    axa.plot(steps, tau_t, 'o-', color=GREEN, ms=3, lw=1.0)
    axa.set_ylabel(r'Crossing threshold $\tau^{*}_{t}$', color=GREEN)
    axa.tick_params(axis='y', colors=GREEN)
    axa.set_ylim(0.58, 0.87)
    axa.set_xlim(0.2, 28.8)
    axa.set_xticks([1, 4, 8, 12, 16, 20, 24, 28])
    axa.set_xlabel('Consolidation step t')
    axab = axa.twinx()
    axab.plot(steps, n_t, 's-', color=PURPLE, ms=2.8, lw=1.0)
    axab.set_ylabel(r'Inventory size $n_t$', color=PURPLE)
    axab.tick_params(axis='y', colors=PURPLE)
    axab.spines['top'].set_visible(False)
    axab.spines['right'].set_visible(True)
    axab.spines['right'].set_color(PURPLE)
    axab.set_ylim(0, 1520)
    axab.annotate('F1: 1,383 cards', xy=(1, F1_N), xytext=(2.6, 1420),
                  fontsize=6.5, color=PURPLE, va='center',
                  arrowprops=dict(arrowstyle='-', lw=0.6, color=PURPLE))
    axab.annotate('F4: 901 cards', xy=(4, F4_N), xytext=(2.4, 470),
                  fontsize=6.5, color=PURPLE, va='center',
                  arrowprops=dict(arrowstyle='-', lw=0.6, color=PURPLE,
                                  shrinkB=2))

    # ---- panel b: per-step quality of the granularity flow ----
    axb.axvspan(14.5, 28.5, color='0.92', zorder=0, lw=0)
    axb.text(18.5, 0.03, 'validity rule fires at step 15',
             transform=axb.get_xaxis_transform(), ha='center', va='bottom',
             fontsize=6, color='0.35')
    lo1, = axb.plot(steps, med_min, 'o-', color=ORANGE, ms=3, lw=1.0,
                    label='Median within-group minimum cosine')
    axb.set_ylabel('Cosine similarity')
    axb.set_ylim(0.55, 0.88)
    axb.set_xlim(0.2, 28.8)
    axb.set_xticks([1, 4, 8, 12, 16, 20, 24, 28])
    axb.set_xlabel('Consolidation step t')
    axbb = axb.twinx()
    lo3, = axbb.plot(steps, med_z, '^-', color=BLUE, ms=3, lw=1.0,
                     label='Median z versus random-group null')
    axbb.axhline(2, color=BLUE, ls=':', lw=0.8, alpha=0.7)
    axbb.text(28.4, 1.93, 'z = 2', fontsize=6, color=BLUE, ha='right',
              va='top')
    axbb.set_ylabel('Median z versus random-group null', color=BLUE)
    axbb.tick_params(axis='y', colors=BLUE)
    axbb.spines['top'].set_visible(False)
    axbb.spines['right'].set_visible(True)
    axbb.spines['right'].set_color(BLUE)
    axbb.set_ylim(1.4, 5.0)
    axb.legend(handles=[lo1, lo3], frameon=False, loc='upper right',
               fontsize=6, handlelength=2.2)

    for ax, L in zip((axa, axb), 'ab'):
        panel_letter(ax, L)
    fig.savefig('paper_tau_percolation/fig5_granularity_flow.pdf')
    fig.savefig('data/experiments/review/fig5_granularity_flow.png')
    plt.close(fig)


if __name__ == '__main__':
    print(f"F1: tau*={F1_TAU}, n={F1_N} | F4: tau*={F4_TAU}, n={F4_N}")
    fig1(); print('fig1 done')
    fig2(); print('fig2 done')
    fig3(); print('fig3 done')
    fig4(); print('fig4 done')
    fig5(); print('fig5 done')
