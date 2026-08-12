"""Rebuild every paper_tau_percolation figure under the v3 architecture.

Main text
  fig1_tau_cohesion.pdf   (fig:tau)   a: master cohesion curves,
                                      b: cohesion-attraction crossing,
                                      c: granularity flow
  fig2_connectivity.pdf   (fig:conn)  threshold-graph connectivity signature
  fig2_before_after.pdf   (fig:merge) anatomy of the F4 consolidation

Appendix
  figA_density.pdf        (fig:taustar)  density dependence tau*(n)      [A1]
  figA_flowquality.pdf    (fig:flowqual) per-step flow quality           [A2]
  figA_mit_replication.pdf(fig:mitrep)   cross-corpus replication        [A3]

The standalone crossing figure (formerly figA_crossing.pdf / fig:cohatt) has
been promoted into panel b of figure 1 and is no longer built by default.

Shared conventions
  x label   'Merge threshold $\\tau$ (decreasing)', axis reversed high->low
  flow axis 'Flow step $t$'
  crossing  'Crossing boundary $\\tau^{*}_{t}$'
  colours   cohesion/crossing/flow  #1f6f5c  green
            per-cluster minimum     #c1550c  orange
            attraction              #4b5fa8  blue-violet
            inventory size/largest  #7a4b8f  purple
            second-largest cluster  #2e7bb5  blue
            counts and nulls        grey
  no coloured background shading; dotted transitions; dashed validity rule
  with its label to the right of the line; no top/right spines; fonttype 42.
"""
import json, colorsys, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 8,
    'axes.linewidth': 0.7, 'pdf.fonttype': 42,
    'axes.labelsize': 8.5, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
    'axes.spines.top': False, 'axes.spines.right': False,
    'xtick.direction': 'out', 'ytick.direction': 'out',
    'savefig.dpi': 400,
})
MM = 1/25.4
GREEN = '#1f6f5c'; ORANGE = '#c1550c'; PURPLE = '#7a4b8f'
BLUE = '#2e7bb5'; RED = '#b0332a'; GREY = '#888888'
VIOLET = '#4b5fa8'          # between-cluster attraction Phi_att
ANN = 8          # in-figure annotation size
LET = 12         # panel letter size

TAU1, TAU2 = 0.818, 0.690           # measured transition means (t1s/t2s)
XL = r'Merge threshold $\tau$ (decreasing)'
FLOWX = r'Flow step $t$'

FLOW = json.load(open('data/experiments/review/flow_states.json'))['steps']
F1_TAU, F1_N = FLOW[0]['tau'], FLOW[0]['n_after']    # 0.8329, 1383
F4_TAU, F4_N = FLOW[3]['tau'], FLOW[3]['n_after']    # 0.7753, 901
STABLE = 0.898                       # replicate statistics stable at/below this


def panel_letter(ax, letter, x=-0.105, y=1.06):
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=LET,
            fontweight='bold', va='bottom', ha='left')


def transition_lines(ax, labels):
    """Dotted vertical lines at tau1 / tau2 with noun-phrase labels."""
    for x, lab, ty, va in labels:
        ax.axvline(x, color='0.3', ls=':', lw=1.0, zorder=1)
        ax.text(x - 0.005, ty, lab, ha='left', va=va, fontsize=ANN,
                color='0.2', zorder=6)


def flow_step_markers(ax, taus, label=r'flow steps $\tau^{*}_{1\ldots 5}$'):
    """Green downward triangles on the top axis at the first flow boundaries."""
    for x in taus:
        ax.plot([x], [1.0], marker='v', ms=5.0, color=GREEN, mec=GREEN,
                transform=ax.get_xaxis_transform(), clip_on=False, zorder=7)
    ax.text(float(np.mean(taus)), 1.035, label, color=GREEN,
            transform=ax.get_xaxis_transform(), ha='center', va='bottom',
            fontsize=ANN)


def load_master():
    b = np.load('data/experiments/review/boot1000_agg.npz')
    taus, mean, sd = b['taus'], b['mean'], b['sd']
    m = taus <= STABLE
    return taus[m], mean[m], sd[m]


# ------------------------------------------------------------------ figure 1
XA_HI, XA_LO = 0.94, 0.60           # shared x-window of panels a and b


def draw_panel_a(ax, t, mean, sd):
    """a: master cohesion statistics.  Draws its own complete x axis."""
    for k, c in [(0, GREEN), (1, ORANGE)]:
        lo = np.clip(mean[:, k] - 2*sd[:, k], 0, 1)
        hi = np.clip(mean[:, k] + 2*sd[:, k], 0, 1)
        ax.fill_between(t, lo, hi, color=c, alpha=0.18, lw=0, zorder=2)
        ax.plot(t, mean[:, k], color=c, lw=1.4, zorder=3)
    transition_lines(ax, [(TAU1, r'$\tau_1$ = 0.818', 0.930, 'top'),
                          (TAU2, r'$\tau_2$ = 0.690', 0.720, 'top')])
    ax.text(0.936, 0.470, 'Pooled mean pairwise similarity', color=GREEN,
            ha='left', va='center', fontsize=ANN)
    ax.text(0.936, 0.372, 'Per-cluster minimum (mean)', color=ORANGE,
            ha='left', va='center', fontsize=ANN)
    ax.set_ylim(0.255, 0.955)
    ax.set_yticks(np.arange(0.2, 0.91, 0.1))
    ax.set_ylabel('Within-cluster cohesion (cosine)')
    ax.set_xlim(XA_HI, XA_LO)
    ax.set_xticks(np.arange(0.90, 0.59, -0.05))
    ax.set_xlabel(XL)


def draw_panel_b(ax, flow5):
    """b: the cohesion-attraction crossing.  Draws its own complete x axis."""
    d = np.load('data/experiments/review/cohdiv_all.npz')
    taus, C, tck, Sck, cross = (d['taus'], d['C'], d['tck'], d['Sck'],
                                d['cross'])
    cm, cs = np.nanmean(C, 0), np.nanstd(C, 0)
    sm, ss = np.nanmean(Sck, 0), np.nanstd(Sck, 0)
    mu, sdv = cross.mean(), cross.std()

    ax.axvspan(mu - 2*sdv, mu + 2*sdv, color='0.90', lw=0, zorder=0)
    # tau2 lies inside the window but outside the informative range: faint,
    # unlabelled.  tau1 is carried over from panel a in the same style.
    ax.axvline(TAU2, color='0.3', ls=':', lw=1.0, alpha=0.35, zorder=1)
    ax.axvline(TAU1, color='0.3', ls=':', lw=1.0, zorder=1)
    ax.text(TAU1 - 0.005, 0.938, r'$\tau_1$ = 0.818', ha='left', va='top',
            fontsize=ANN, color='0.2', zorder=6)
    m = (taus >= XA_LO) & (taus <= XA_HI)
    ax.fill_between(taus[m], (cm-2*cs)[m], (cm+2*cs)[m], color=GREEN,
                    alpha=0.18, lw=0, zorder=2)
    ax.plot(taus[m], cm[m], color=GREEN, lw=1.4, zorder=3)
    mk = (tck >= XA_LO) & (tck <= XA_HI)
    ax.fill_between(tck[mk], (sm-2*ss)[mk], (sm+2*ss)[mk], color=VIOLET,
                    alpha=0.18, lw=0, zorder=2)
    ax.plot(tck[mk], sm[mk], color=VIOLET, lw=1.4, zorder=3)
    ycross = float(np.interp(mu, taus[::-1], cm[::-1]))
    ax.annotate('$\\tau^{*}$ = 0.828 $\\pm$ 0.004\n(full inventory 0.833)',
                xy=(mu, ycross), xytext=(0.7360, 0.905), fontsize=ANN,
                color='0.2', ha='left', va='center',
                arrowprops=dict(arrowstyle='-', lw=0.7, color='0.4',
                                shrinkB=2), zorder=6)
    flow_step_markers(ax, flow5)
    hcoh = plt.Line2D([], [], color=GREEN, lw=1.4,
                      label=r'Within-cluster cohesion $\Phi_{\mathrm{coh}}$')
    hatt = plt.Line2D([], [], color=VIOLET, lw=1.4,
                      label=r'Between-cluster attraction $\Phi_{\mathrm{att}}$')
    ax.legend(handles=[hcoh, hatt], frameon=False, loc='lower left',
              fontsize=ANN, handlelength=1.8, bbox_to_anchor=(0.015, 0.015))
    ax.set_ylim(0.552, 0.958)
    ax.set_yticks(np.arange(0.55, 0.96, 0.05))
    ax.set_ylabel('Cosine similarity')
    ax.set_xlim(XA_HI, XA_LO)
    ax.set_xticks(np.arange(0.90, 0.59, -0.05))
    ax.set_xlabel(XL)


def draw_panel_c(ax, ax_right, steps, tau_t, n_t):
    """c: granularity flow trajectory.  ax_right is the twinx of ax."""
    ax.axvline(14.5, color='0.35', ls=(0, (4, 2.5)), lw=1.0, zorder=2)
    ax.text(15.1, 0.975, 'validity rule\nfires (step 15)',
            transform=ax.get_xaxis_transform(), ha='left', va='top',
            fontsize=ANN, color='0.35')
    l1, = ax.plot(steps, tau_t, 'o-', color=GREEN, ms=4.2, lw=1.3,
                  label=r'Crossing boundary $\tau^{*}_{t}$', zorder=4)
    ax.set_ylabel(r'Crossing boundary $\tau^{*}_{t}$', color=GREEN)
    ax.tick_params(axis='y', colors=GREEN)
    ax.set_ylim(0.598, 0.845)
    ax.set_xlim(0.2, 28.8)
    ax.set_xticks([1, 4, 7, 10, 13, 16, 19, 22, 25, 28])
    ax.set_xlabel(FLOWX)

    l2, = ax_right.plot(steps, n_t, 's-', color=PURPLE, ms=4.0, lw=1.3,
                        label=r'Inventory size $n_t$', zorder=4)
    ax_right.set_ylabel(r'Inventory size $n_t$', color=PURPLE)
    ax_right.tick_params(axis='y', colors=PURPLE)
    ax_right.spines['top'].set_visible(False)
    ax_right.spines['right'].set_visible(True)
    ax_right.spines['right'].set_color(PURPLE)
    ax_right.set_ylim(0, 1470)
    ax_right.annotate('F1 (0.833, 1,383 cards)', xy=(1.2, F1_N),
                      xytext=(2.6, 1432), fontsize=ANN, color='0.2',
                      va='center', ha='left',
                      arrowprops=dict(arrowstyle='-', lw=0.7, color='0.45',
                                      shrinkB=3))
    # F4 leader points at the green boundary marker and the label is shifted
    # right and up into the empty band, so it never touches the green curve.
    ax.annotate('F4 (0.775, 901 cards)', xy=(4.15, F4_TAU),
                xytext=(5.6, 0.7980), fontsize=ANN, color='0.2',
                va='center', ha='left',
                arrowprops=dict(arrowstyle='-', lw=0.7, color='0.45',
                                shrinkB=4), zorder=6)
    ax_right.text(27.9, n_t[-1] + 60, '32', fontsize=ANN, color=PURPLE,
                  ha='center', va='bottom')
    ax.legend(handles=[l1, l2], frameon=False, loc='lower left',
              fontsize=ANN, handlelength=2.2, bbox_to_anchor=(0.02, 0.02))


def fig1():
    t, mean, sd = load_master()
    steps = np.arange(1, len(FLOW) + 1)
    tau_t = np.array([s['tau'] for s in FLOW])
    n_t = np.array([s['n_after'] for s in FLOW], float)
    flow5 = [s['tau'] for s in FLOW[:5]]

    # ---------------------------------------------------- composite figure
    fig = plt.figure(figsize=(150*MM, 268*MM))
    # panels a and b share the x-window and the x scaling; the tick labels and
    # the x label are drawn once, under b.  panel c carries its own x axis.
    gsab = fig.add_gridspec(2, 1, left=0.125, right=0.905,
                            top=0.968, bottom=0.400, hspace=0.20,
                            height_ratios=[1.06, 1.0])
    gsc = fig.add_gridspec(1, 1, left=0.125, right=0.905,
                           top=0.310, bottom=0.050)
    axa = fig.add_subplot(gsab[0])
    axb = fig.add_subplot(gsab[1], sharex=axa)
    axc = fig.add_subplot(gsc[0])

    draw_panel_a(axa, t, mean, sd)
    draw_panel_b(axb, flow5)
    draw_panel_c(axc, axc.twinx(), steps, tau_t, n_t)

    # shared x axis: a hands its tick labels and its x label over to b
    axa.set_xlabel('')
    axa.tick_params(axis='x', labelbottom=False)

    panel_letter(axa, 'a', y=1.02)
    panel_letter(axb, 'b', y=1.075)
    panel_letter(axc, 'c', y=1.03)
    fig.savefig('data/experiments/review/tau_cohesion_nature_094.png')
    fig.savefig('data/experiments/review/fig1_tau_cohesion.png')
    fig.savefig('paper_tau_percolation/fig1_tau_cohesion.pdf')
    plt.close(fig)

    # ------------------------------------------- standalone single panels
    # same draw_panel_* code, one figure per panel, no panel letter: these are
    # meant to be reused on their own (slides, project page).
    def _standalone(key, draw):
        f = plt.figure(figsize=(150*MM, 95*MM))
        gs = f.add_gridspec(1, 1, left=0.135, right=0.895,
                            top=0.900, bottom=0.165)
        ax = f.add_subplot(gs[0])
        draw(ax)
        f.savefig(f'data/experiments/review/fig1_panel_{key}.png')
        f.savefig(f'paper_tau_percolation/fig1_panel_{key}.pdf')
        plt.close(f)

    _standalone('a', lambda ax: draw_panel_a(ax, t, mean, sd))
    _standalone('b', lambda ax: draw_panel_b(ax, flow5))
    _standalone('c', lambda ax: draw_panel_c(ax, ax.twinx(), steps, tau_t, n_t))



# ------------------------------------------------------------------ figure 2
def fig2_connectivity():
    t, mean, sd = load_master()
    fig, ax = plt.subplots(figsize=(150*MM, 85*MM))
    fig.subplots_adjust(left=0.095, right=0.985, top=0.955, bottom=0.165)
    ax.plot(t, np.maximum(mean[:, 2]/0.8, 1), color=GREY, lw=1.3,
            label='Number of clusters')
    ax.plot(t, np.maximum(mean[:, 3]/0.8, 1), color=PURPLE, lw=1.3,
            label='Largest cluster size')
    ax.plot(t, np.maximum(mean[:, 4]/0.8, 1), color=BLUE, lw=1.3,
            label='Second-largest cluster size')
    for x, lab in [(TAU1, r'$\tau_1$ = 0.818'), (TAU2, r'$\tau_2$ = 0.690')]:
        ax.axvline(x, color='0.3', ls=':', lw=1.0, zorder=1)
        ax.text(x - 0.005, 0.975, lab, transform=ax.get_xaxis_transform(),
                ha='left', va='top', fontsize=ANN, color='0.2')
    ax.set_yscale('log')
    ax.set_ylim(0.82, 4200)
    ax.set_xlim(0.905, 0.495)
    ax.set_xticks(np.arange(0.90, 0.49, -0.05))
    ax.set_xlabel(XL)
    ax.set_ylabel('Count or size (log scale)')
    ax.legend(frameon=False, loc='center right', bbox_to_anchor=(1.0, 0.46),
              fontsize=ANN, handlelength=1.8)
    fig.savefig('data/experiments/review/fig2_connectivity.png')
    fig.savefig('paper_tau_percolation/fig2_connectivity.pdf')
    plt.close(fig)


# ------------------------------------------------------- figure 3 (F4 anatomy)
def fig3_before_after(tier='f4'):
    """Anatomy of one consolidation. tier is 'f4' or 'f5'; both are kept."""
    TIER = {
        'f4': dict(state='data/experiments/review/flow4_state.json',
                   name='F4', tau=FLOW[3]['tau'], sub=4,
                   png='data/experiments/review/fig2_before_after.png',
                   pdf='paper_tau_percolation/fig2_before_after.pdf'),
        'f5': dict(state='data/experiments/review/f5_state.json',
                   name='F5', tau=FLOW[4]['tau'], sub=5,
                   png='data/experiments/review/fig2_before_after_f5.png',
                   pdf='paper_tau_percolation/fig2_before_after_f5.pdf'),
    }[tier]
    master = json.load(open('data/experiments/stage1/out/master.json'))['cards']
    f4 = json.load(open(TIER['state']))['cards']
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
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.34,
                          wspace=0.27, left=0.065, right=0.975, top=0.945,
                          bottom=0.135)
    axa = fig.add_subplot(gs[0, 0]); axb = fig.add_subplot(gs[0, 1])
    axc = fig.add_subplot(gs[1, 0]); axd = fig.add_subplot(gs[1, 1])

    # a: master with F4 cumulative merge groups
    axa.scatter(XY[ung, 0], XY[ung, 1], s=2, c='0.82', lw=0, zorder=1)
    from matplotlib.patches import FancyArrowPatch
    for g, r, col in zip(groups, reps, gcol):
        for i in g:
            if i != r:
                axa.add_patch(FancyArrowPatch(
                    (XY[i, 0], XY[i, 1]), (XY[r, 0], XY[r, 1]),
                    connectionstyle='arc3,rad=0.22', arrowstyle='-',
                    color=col, lw=0.25, alpha=0.5, zorder=2))
        axa.scatter(XY[g, 0], XY[g, 1], s=4, color=[col], lw=0, zorder=3)
    axa.set_title('Master inventory (1,612 cards)', fontsize=8.5)
    axa.text(0.5, -0.045,
             f'{len(groups)} cumulative merge groups · '
             f'{int(sizes.sum())} cards involved',
             transform=axa.transAxes, ha='center', fontsize=ANN, color='0.45')

    # b: F4 state, groups collapsed to representatives
    axb.scatter(XY[ung, 0], XY[ung, 1], s=2, c='0.82', lw=0, zorder=1)
    for g, r, col in zip(groups, reps, gcol):
        ghosts = [i for i in g if i != r]
        axb.scatter(XY[ghosts, 0], XY[ghosts, 1], s=1.5, c='0.92', lw=0,
                    zorder=0)
        axb.scatter(XY[r, 0], XY[r, 1], s=3 + 1.8*len(g), color=[col],
                    lw=0.4, edgecolor='white', zorder=3)
    axb.set_title(f"Compression tier {TIER['name']} ({len(f4):,} cards)",
                  fontsize=8.5)
    axb.text(0.5, -0.045, 'merge groups collapsed to medoid representatives',
             transform=axb.transAxes, ha='center', fontsize=ANN, color='0.45')
    for a in (axa, axb):
        a.set_xticks([]); a.set_yticks([])
        a.spines[['left', 'bottom']].set_visible(False)

    # c: stacked histogram of group sizes by family
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
            axc.text(x, btot + 2, str(int(btot)), ha='center', fontsize=7,
                     color='0.3')
    axc.set_xlabel('Merge-group size')
    axc.set_ylabel('Number of merge groups')
    axc.set_xticks(xs)
    axc.set_xticklabels([str(x) for x in xs[:-1]] + ['11+'])
    axc.set_ylim(0, bottom.max()*1.12)

    # d: min within-group cosine vs size, with random-group null
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
    axd.plot(uniq, null_md, color='0.6', lw=0.8)
    jit = np.exp(rng3.normal(0, 0.022, len(sizes)))
    for f in FAMS:
        m = [i for i, fm in enumerate(gfam) if fm == f]
        axd.scatter(sizes[m]*jit[m], gmin[m], s=6, color=FCOL[f], lw=0,
                    alpha=0.85, zorder=3)
    axd.axhline(TIER['tau'], color='0.3', ls=(0, (4, 2.5)), lw=0.9)
    xmax = float(sizes.max())*1.22
    axd.text(xmax*0.97, TIER['tau'] + 0.014,
             r'$\tau^{*}_{%d}$ = %.3f' % (TIER['sub'], TIER['tau']),
             fontsize=ANN, ha='right', color='0.3')
    axd.set_xscale('log')
    axd.set_xlim(1.8, xmax)
    ticks = [t for t in (2, 3, 4, 5, 7, 10, 15, 20, 30, 50, 70, 100)
             if t <= xmax]
    axd.set_xticks(ticks)
    axd.set_xticklabels([str(t) for t in ticks])
    axd.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    axd.set_xlabel('Merge-group size (log scale)')
    axd.set_ylabel('Minimum within-group cosine')

    for a, L in zip((axa, axb, axc, axd), 'abcd'):
        a.text(-0.05, 1.06, L, transform=a.transAxes, fontsize=LET,
               fontweight='bold', va='bottom')
    handles = [plt.Line2D([], [], marker='o', ls='', ms=5, color=FCOL[f],
               label=FNAME[f]) for f in FAMS]
    handles.append(plt.Line2D([], [], marker='o', ls='', ms=5, color='0.82',
                   label='Never merged'))
    fig.legend(handles=handles, loc='lower center', ncol=4, frameon=False,
               fontsize=8, bbox_to_anchor=(0.5, 0.015))
    fig.savefig(TIER['png'])
    fig.savefig(TIER['pdf'])
    print(f"fig3 {TIER['name']}: {len(groups)} groups, "
          f"{int(sizes.sum())} cards involved, max group {int(sizes.max())}")
    plt.close(fig)


# ------------------------------------------------- appendix A1: the crossing
def figA_crossing():
    d = np.load('data/experiments/review/cohdiv_all.npz')
    taus, C, tck, Sck, cross = d['taus'], d['C'], d['tck'], d['Sck'], d['cross']
    cm, cs = np.nanmean(C, 0), np.nanstd(C, 0)
    sm, ss = np.nanmean(Sck, 0), np.nanstd(Sck, 0)
    mu, sdv = cross.mean(), cross.std()

    fig, ax = plt.subplots(figsize=(120*MM, 80*MM))
    fig.subplots_adjust(left=0.125, right=0.965, top=0.955, bottom=0.155)
    ax.axvspan(mu - 2*sdv, mu + 2*sdv, color='0.90', lw=0, zorder=0)
    ax.axvline(mu, color='0.35', ls=':', lw=1.0, zorder=1)
    m = taus >= 0.60
    ax.fill_between(taus[m], (cm-2*cs)[m], (cm+2*cs)[m], color=GREEN,
                    alpha=0.16, lw=0)
    ax.plot(taus[m], cm[m], color=GREEN, lw=1.3,
            label=r'Within-cluster cohesion $\Phi_{\mathrm{coh}}$')
    mk = tck >= 0.60
    ax.fill_between(tck[mk], (sm-2*ss)[mk], (sm+2*ss)[mk], color=RED,
                    alpha=0.16, lw=0)
    ax.plot(tck[mk], sm[mk], color=RED, lw=1.3,
            label=r'Between-cluster attraction $\Phi_{\mathrm{att}}$')
    ycross = float(np.interp(mu, taus[::-1], cm[::-1]))
    ax.annotate('$\\tau^{*}$ = 0.828 $\\pm$ 0.004\n(full inventory 0.833)',
                xy=(mu, ycross), xytext=(0.8175, 0.878), fontsize=ANN,
                color='0.2', ha='left', va='center',
                arrowprops=dict(arrowstyle='-', lw=0.7, color='0.4',
                                shrinkB=2))
    ax.set_xlim(taus.max(), 0.60)
    ax.set_ylim(0.55, 0.965)
    ax.set_xlabel(XL)
    ax.set_ylabel('Cosine similarity')
    ax.legend(frameon=False, loc='lower left', fontsize=ANN,
              handlelength=1.8, bbox_to_anchor=(0.02, 0.02))
    fig.savefig('data/experiments/review/figA_crossing.png')
    fig.savefig('paper_tau_percolation/figA_crossing.pdf')
    plt.close(fig)


# --------------------------------------------- appendix A2: density of tau*
def crossing_per_replicate(taus, C, S):
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


def figA_density():
    rows = []
    for f in sorted(glob.glob('data/experiments/review/cohdiv_frac_*.npz')):
        d = np.load(f)
        cr = crossing_per_replicate(d['taus'], d['C'], d['S'])
        if len(cr):
            rows.append((float(np.mean(d['ns'])), cr.mean(), cr.std()))
    rows.sort()
    n = np.array([r[0] for r in rows]); m = np.array([r[1] for r in rows])
    s = np.array([r[2] for r in rows])

    fig, ax = plt.subplots(figsize=(100*MM, 70*MM))
    fig.subplots_adjust(left=0.155, right=0.975, top=0.955, bottom=0.165)
    ax.axhline(0.828, color='0.55', ls=':', lw=1.0, zorder=1)
    ax.text(0.025, 0.8262, r'$\tau^{*}$ at 80% subsamples', transform=
            ax.get_yaxis_transform(), ha='left', va='top', fontsize=ANN,
            color='0.4')
    ax.errorbar(n, m, yerr=2*s, fmt='o', ms=4.0, color=GREEN, elinewidth=0.9,
                capsize=2.2, lw=0, zorder=4)
    a, b = np.polyfit(np.log(n), m, 1)
    xs = np.geomspace(n.min()*0.9, n.max()*1.1, 100)
    ax.plot(xs, a*np.log(xs) + b, ls=(0, (4, 2.5)), color='0.45', lw=1.0,
            zorder=3)
    ax.text(0.975, 0.04, rf'$\tau^{{*}} \approx {b:.3f} + {a:.3f}\,\ln n$',
            transform=ax.transAxes, fontsize=ANN, color='0.3', va='bottom',
            ha='right')
    ax.set_xscale('log')
    ax.set_xticks([400, 600, 800, 1000, 1600])
    ax.set_xticklabels(['400', '600', '800', '1,000', '1,600'])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlabel(r'Inventory size $n$ (log scale)')
    ax.set_ylabel(r'Crossing boundary $\tau^{*}$')
    fig.savefig('data/experiments/review/figA_density.png')
    fig.savefig('paper_tau_percolation/figA_density.pdf')
    plt.close(fig)


# ------------------------------------------ appendix A3: per-step flow quality
def figA_flowquality():
    steps = np.arange(1, len(FLOW) + 1)
    med_min = np.array([s['med_min'] for s in FLOW])
    med_z = np.array([s['med_z'] for s in FLOW])

    fig, ax = plt.subplots(figsize=(120*MM, 75*MM))
    fig.subplots_adjust(left=0.135, right=0.855, top=0.955, bottom=0.165)
    ax.axvline(14.5, color='0.35', ls=(0, (4, 2.5)), lw=1.0, zorder=2)
    ax.text(15.1, 0.715, 'validity rule fires (step 15)',
            transform=ax.get_xaxis_transform(), ha='left', va='bottom',
            fontsize=ANN, color='0.35')
    l1, = ax.plot(steps, med_min, 'o-', color=ORANGE, ms=4.0, lw=1.3,
                  label='Median within-group minimum cosine', zorder=4)
    ax.set_ylabel('Median within-group minimum cosine', color=ORANGE)
    ax.tick_params(axis='y', colors=ORANGE)
    ax.set_ylim(0.55, 0.88)
    ax.set_xlim(0.2, 28.8)
    ax.set_xticks([1, 4, 7, 10, 13, 16, 19, 22, 25, 28])
    ax.set_xlabel(FLOWX)

    axr = ax.twinx()
    l2, = axr.plot(steps, med_z, '^-', color=BLUE, ms=4.2, lw=1.3,
                   label='Median $z$ versus random-group null', zorder=4)
    axr.axhline(2, color=BLUE, ls=':', lw=1.0, alpha=0.8)
    axr.text(0.6, 2.06, '$z$ = 2', fontsize=ANN, color=BLUE, ha='left',
             va='bottom')
    axr.set_ylabel('Median $z$ versus random-group null', color=BLUE)
    axr.tick_params(axis='y', colors=BLUE)
    axr.spines['top'].set_visible(False)
    axr.spines['right'].set_visible(True)
    axr.spines['right'].set_color(BLUE)
    axr.set_ylim(1.4, 5.2)
    ax.legend(handles=[l1, l2], loc='upper right', fontsize=ANN,
              handlelength=2.2, bbox_to_anchor=(1.0, 1.0), frameon=True,
              facecolor='white', edgecolor='none', framealpha=1.0)
    fig.savefig('data/experiments/review/figA_flowquality.png')
    fig.savefig('paper_tau_percolation/figA_flowquality.pdf')
    plt.close(fig)


# ------------------------------------------ appendix A4: MIT v4 replication
def figA_mit():
    BASE = 'data/experiments/mit_replication'
    d = np.load(f'{BASE}/mit_boot_agg.npz')
    taus, mean, sd = d['taus'], d['mean'], d['sd']
    st = json.load(open(f'{BASE}/mit_flow_states.json'))['steps']
    m = (taus <= 0.95) & (taus >= 0.40)
    t, mean, sd = taus[m], mean[m], sd[m]
    T1, T2 = float(d['t1s'].mean()), float(d['t2s'].mean())

    fig = plt.figure(figsize=(183*MM, 78*MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.40,
                          left=0.075, right=0.90, top=0.895, bottom=0.165)
    axa = fig.add_subplot(gs[0]); axb = fig.add_subplot(gs[1])

    for k, c in [(0, GREEN), (1, ORANGE)]:
        lo = np.clip(mean[:, k] - 2*sd[:, k], 0, 1)
        hi = np.clip(mean[:, k] + 2*sd[:, k], 0, 1)
        axa.fill_between(t, lo, hi, color=c, alpha=0.18, lw=0, zorder=2)
        axa.plot(t, mean[:, k], color=c, lw=1.3, zorder=3)
    axa.axvline(T1, color='0.3', ls=':', lw=1.0)
    axa.axvline(T2, color='0.3', ls=':', lw=1.0)
    axa.text(T1 - 0.008, 1.055, r'$\tau_1$ = %.3f' % T1, ha='left', va='center',
             fontsize=ANN, color='0.2')
    axa.text(T2 - 0.008, 1.055, r'$\tau_2$ = %.3f' % T2, ha='left', va='center',
             fontsize=ANN, color='0.2')
    flow_step_markers(axa, [s['tau'] for s in st[:5]])
    axa.text(0.612, 0.630, 'Pooled mean\npairwise similarity', color=GREEN,
             ha='left', va='center', fontsize=ANN, linespacing=1.35)
    axa.text(0.612, 0.290, 'Per-cluster minimum\n(mean)', color=ORANGE,
             ha='left', va='center', fontsize=ANN, linespacing=1.35)
    axa.set_xlim(0.952, 0.398)
    axa.set_ylim(0.0, 1.20)
    axa.set_yticks(np.arange(0.0, 1.01, 0.2))
    axa.set_xticks([0.95, 0.85, 0.75, 0.65, 0.55, 0.45])
    axa.set_xlabel(XL)
    axa.set_ylabel('Within-cluster cohesion (cosine)')

    fs = np.arange(1, len(st) + 1)
    tau_t = np.array([s['tau'] for s in st])
    n_t = np.array([s['n_after'] for s in st], float)
    axb.plot(fs, tau_t, 'o-', color=GREEN, ms=4.2, lw=1.3)
    for x, y in zip(fs, tau_t):
        last = x == fs[-1]
        axb.annotate(f'{y:.4f}', (x, y), textcoords='offset points',
                     xytext=(7, 2), fontsize=7.5, color=GREEN, ha='left')
    axb.set_ylabel(r'Crossing boundary $\tau^{*}_{t}$', color=GREEN,
                   fontsize=8)
    axb.tick_params(axis='y', colors=GREEN)
    axb.set_ylim(0.720, 0.848)
    axb.set_xlim(-0.75, 6.30)
    axb.set_xticks(range(0, 6))
    axb.set_xlabel(FLOWX)

    axbb = axb.twinx()
    n_all = np.concatenate([[st[0]['n_before']], n_t])
    axbb.plot(np.arange(0, len(st) + 1), n_all, 's-', color=PURPLE,
              ms=4.0, lw=1.3)
    for x, y in zip(np.arange(0, len(st) + 1), n_all):
        first = x == 0
        axbb.annotate(f'{int(y):,}', (x, y), textcoords='offset points',
                      xytext=((8, -3) if first else (-7, -3)), fontsize=7.5,
                      color=PURPLE, ha=('left' if first else 'right'))
    axbb.set_ylabel(r'Inventory size $n_t$', color=PURPLE, fontsize=8)
    axbb.tick_params(axis='y', colors=PURPLE)
    axbb.spines['top'].set_visible(False)
    axbb.spines['right'].set_visible(True)
    axbb.spines['right'].set_color(PURPLE)
    axbb.set_ylim(600, 1980)

    panel_letter(axa, 'a', x=-0.085, y=1.09)
    panel_letter(axb, 'b', x=-0.135, y=1.09)
    fig.savefig('data/experiments/review/figA_mit_replication.png')
    fig.savefig('paper_tau_percolation/figA_mit_replication.pdf')
    plt.close(fig)


# ------------------------- review overview: master inventory, MIT-style layout
def figA_ours():
    """Two-panel summary of our own inventory, laid out like the MIT figure."""
    t, mean, sd = load_master()
    st = FLOW

    fig = plt.figure(figsize=(183*MM, 78*MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=0.40,
                          left=0.075, right=0.90, top=0.895, bottom=0.165)
    axa = fig.add_subplot(gs[0]); axb = fig.add_subplot(gs[1])

    for k, c in [(0, GREEN), (1, ORANGE)]:
        lo = np.clip(mean[:, k] - 2*sd[:, k], 0, 1)
        hi = np.clip(mean[:, k] + 2*sd[:, k], 0, 1)
        axa.fill_between(t, lo, hi, color=c, alpha=0.18, lw=0, zorder=2)
        axa.plot(t, mean[:, k], color=c, lw=1.3, zorder=3)
    axa.axvline(TAU1, color='0.3', ls=':', lw=1.0)
    axa.axvline(TAU2, color='0.3', ls=':', lw=1.0)
    axa.text(TAU1 - 0.006, 0.905, r'$\tau_1$ = 0.818', ha='left', va='center',
             fontsize=ANN, color='0.2')
    axa.text(TAU2 - 0.006, 0.905, r'$\tau_2$ = 0.690', ha='left', va='center',
             fontsize=ANN, color='0.2')
    flow_step_markers(axa, [s['tau'] for s in st[:5]])
    axa.text(0.893, 0.470, 'Pooled mean\npairwise similarity', color=GREEN,
             ha='left', va='center', fontsize=ANN, linespacing=1.35)
    axa.text(0.893, 0.330, 'Per-cluster minimum\n(mean)', color=ORANGE,
             ha='left', va='center', fontsize=ANN, linespacing=1.35)
    axa.set_xlim(0.902, 0.598)
    axa.set_ylim(0.255, 1.02)
    axa.set_yticks(np.arange(0.3, 0.91, 0.1))
    axa.set_xticks(np.arange(0.90, 0.59, -0.05))
    axa.set_xlabel(XL)
    axa.set_ylabel('Within-cluster cohesion (cosine)')

    n_show = 5
    fs = np.arange(1, n_show + 1)
    tau_t = np.array([s['tau'] for s in st[:n_show]])
    n_t = np.array([s['n_after'] for s in st[:n_show]], float)
    axb.plot(fs, tau_t, 'o-', color=GREEN, ms=4.2, lw=1.3)
    for x, y in zip(fs, tau_t):
        last = x == fs[-1]
        axb.annotate(f'{y:.4f}', (x, y), textcoords='offset points',
                     xytext=(7, 2), fontsize=7.5, color=GREEN, ha='left')
    axb.set_ylabel(r'Crossing boundary $\tau^{*}_{t}$', color=GREEN, fontsize=8)
    axb.tick_params(axis='y', colors=GREEN)
    axb.set_ylim(0.752, 0.856)
    axb.set_xlim(-0.75, 6.30)
    axb.set_xticks(range(0, 6))
    axb.set_xlabel(FLOWX)

    axbb = axb.twinx()
    n_all = np.concatenate([[st[0]['n_before']], n_t])
    axbb.plot(np.arange(0, n_show + 1), n_all, 's-', color=PURPLE, ms=4.0, lw=1.3)
    for x, y in zip(np.arange(0, n_show + 1), n_all):
        first = x == 0
        axbb.annotate(f'{int(y):,}', (x, y), textcoords='offset points',
                      xytext=((8, -3) if first else (-7, -3)), fontsize=7.5,
                      color=PURPLE, ha=('left' if first else 'right'))
    axbb.set_ylabel(r'Inventory size $n_t$', color=PURPLE, fontsize=8)
    axbb.tick_params(axis='y', colors=PURPLE)
    axbb.spines['top'].set_visible(False)
    axbb.spines['right'].set_visible(True)
    axbb.spines['right'].set_color(PURPLE)
    axbb.set_ylim(700, 1760)

    panel_letter(axa, 'a', x=-0.085, y=1.09)
    panel_letter(axb, 'b', x=-0.135, y=1.09)
    fig.savefig('data/experiments/review/figA_master_overview.png')
    plt.close(fig)


if __name__ == '__main__':
    import sys
    which = sys.argv[1:] or ['1', '2', '3', 'A1', 'A2', 'A3']
    print(f'F1: tau*={F1_TAU}, n={F1_N} | F4: tau*={F4_TAU}, n={F4_N}')
    # 'crossing' is retained for reference only; it is no longer a paper
    # figure (it became panel b of figure 1) and is not in the default set.
    jobs = {'1': fig1, '2': fig2_connectivity, '3': fig3_before_after,
            'A1': figA_density, 'A2': figA_flowquality, 'A3': figA_mit,
            'A4': figA_ours,
            '3f5': lambda: fig3_before_after('f5'),
            'crossing': figA_crossing}
    for k in which:
        jobs[k](); print(f'fig {k} done', flush=True)
