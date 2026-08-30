#!/usr/bin/env python3
"""Regenerate the release figure set and the domain table on the 629-card basis.

Every figure is derived from the released artifacts only:
  - handover/.../01_data/L4_*.csv        (full-column card data)
  - releases/.../manifest.json           (reconciliation and round-2 stage record)
  - releases/.../validation/final_release_qa.json
  - releases/.../validation/Audit_Correction_Log.csv

Figures that depend on EM or Hybrid EM scores are NOT regenerated: the scores
were removed from the release by AC-04/AC-10, rerunning EM is forbidden, and
publishing score status contradicts AC-12. Those files are moved to
figures/archive_pre_audit/ instead.

Style follows the house standard: Times New Roman, Nature figure geometry,
categorical charts carry the global mean as a dashed grey reference line.
"""
import csv, json, shutil, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/Users/deep1003/data3/dci_ai_infra_research/06_analysis/styles')
from nature_style import apply_nature_style, NATURE_COLORS, W1, W2, add_global_mean, save

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
REL = ROOT / 'releases/RAI-Risk-Taxonomy-2.0-master'
HOV = ROOT / 'handover/RAI-Risk-Taxonomy-2.0-master_20260829'
FIG = REL / 'figures'
TAB = REL / 'tables'
ARCH = FIG / 'archive_pre_audit'

DOMAINS = ['General AI', 'Agentic AI', 'Physical AI']
SHORT = ['General', 'Agentic', 'Physical']
DCOL = {'General AI': NATURE_COLORS[0], 'Agentic AI': NATURE_COLORS[1], 'Physical AI': NATURE_COLORS[2]}

# Figures that cannot be rebuilt truthfully on the 629 basis.
RETIRE = {
    'em_quality_diagnostics.png': 'EM score, margin and stability distributions; the score columns were removed by AC-04/AC-10 and EM must not be rerun.',
    'em_baseline_comparison.png': 'Pre-keyword baseline versus keyword-augmented EM outcomes; a pipeline-history comparison that no longer describes the released set.',
    'round2_mapping_score_status.png': 'Mapping score status counts; AC-12 removed score status from the published release.',
    'round2_similarity_top10.png': 'Highest-similarity card pairs, derived from embedding similarity scores that are not published.',
    'definition_grounding_by_domain.png': 'Definition grounding actions; at 629 this field is dominated by the same score-status labels AC-12 withdrew from publication.',
    'semantic_near_duplicate_review.png': 'Round-1 near-duplicate candidate decisions; superseded by audit_consolidation_by_correction.png.',
    'round2_validation.png': 'Five recorded post-build checks, all PASS; five identical bars carry no information that the Validation Record table does not already state.',
    'round2_language_edits.png': 'Round-2 copyedit operations, which were 0 in Korean and 0 in English; a chart of two zeros carries no information.',
}


def load_cards():
    cards = []
    for fn, dom in zip(['L4_General.csv', 'L4_Agentic.csv', 'L4_Physical.csv'], DOMAINS):
        with (HOV / '01_data' / fn).open(encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                r['_domain'] = dom
                cards.append(r)
    return cards


MINUS = '\u2212'


def sgn(v):
    return f'+{v:,}' if v > 0 else (f'{MINUS}{abs(v):,}' if v < 0 else '0')


def bar_labels(ax, bars, fmt='{:,.0f}', pad=2):
    for b in bars:
        ax.annotate(fmt.format(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha='center', va='bottom', fontsize=6, xytext=(0, pad), textcoords='offset points')


def main():
    apply_nature_style()
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    ARCH.mkdir(parents=True, exist_ok=True)

    cards = load_cards()
    manifest = json.loads((REL / 'manifest.json').read_text(encoding='utf-8'))
    s = manifest['summary']
    qa = json.loads((REL / 'validation/final_release_qa.json').read_text(encoding='utf-8'))
    with (REL / 'validation/Audit_Correction_Log.csv').open(encoding='utf-8-sig', newline='') as f:
        ac_log = list(csv.DictReader(f))

    final = [sum(1 for c in cards if c['_domain'] == d) for d in DOMAINS]
    source = [s['source_counts'][d.replace(' AI', '')] for d in DOMAINS]
    total = sum(final)
    assert total == s['final_total'] == 629, (total, s['final_total'])

    # 1. Domain counts, previous release versus current release ---------------
    fig, ax = plt.subplots(figsize=(W2, W2 * 0.42))
    x = range(3); w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], source, w, color='#B4BCC6', label='Previous release (798)')
    b2 = ax.bar([i + w / 2 for i in x], final, w, color=[DCOL[d] for d in DOMAINS],
                label=f'Audited release ({total})')
    bar_labels(ax, b1); bar_labels(ax, b2)
    add_global_mean(ax, final, 'h', label=f'Current mean per domain ({total/3:.0f})')
    ax.set_xticks(list(x)); ax.set_xticklabels(SHORT)
    ax.set_ylabel('L4 risk cards')
    ax.set_title('Domain counts before and after the line-by-line audit')
    ax.set_ylim(0, max(source) * 1.18)
    ax.legend(loc='upper center', bbox_to_anchor=(0.62, 1.0), ncol=3)
    save(fig, FIG / 'domain_counts_before_after.png')
    save_copy = FIG / 'round2_domain_counts.png'

    # 2. Same comparison, kept under the historical filename ------------------
    fig, ax = plt.subplots(figsize=(W2, W2 * 0.42))
    net = [f - so for so, f in zip(source, final)]
    bars = ax.bar(SHORT, net, color=[DCOL[d] for d in DOMAINS])
    for b, n in zip(bars, net):
        ax.annotate(sgn(n), (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha='center', va='bottom' if n >= 0 else 'top', fontsize=6,
                    xytext=(0, 2 if n >= 0 else -2), textcoords='offset points')
    add_global_mean(ax, net, 'h', label=f'Mean net change ({sgn(round(sum(net)/3))})')
    ax.axhline(0, color='#333333', lw=0.5)
    ax.set_ylim(min(net) * 1.22, max(0, max(net)) + abs(min(net)) * 0.10)
    ax.set_ylabel('Net change in L4 cards')
    ax.set_title('Net change per domain, previous release to audited release')
    ax.legend(loc='lower right')
    save(fig, save_copy)

    # 3. Reconciliation waterfall --------------------------------------------
    steps = ['Previous\nrelease', 'Explicit\ndeletions', 'Absorbed', 'Added', 'Audited\nrelease']
    deltas = [None, -s['deleted'], -s['merged_away'], s['split_net_addition'], None]
    base, bottoms, heights, cols = s['source_total'], [], [], []
    for i, d in enumerate(steps):
        if d is steps[0]:
            bottoms.append(0); heights.append(s['source_total']); cols.append('#6E6E6E')
        elif d is steps[-1]:
            bottoms.append(0); heights.append(total); cols.append(NATURE_COLORS[0])
        else:
            delta = deltas[i]
            new = base + delta
            bottoms.append(min(base, new)); heights.append(abs(delta))
            cols.append(NATURE_COLORS[3] if delta < 0 else NATURE_COLORS[2])
            base = new
    assert base == total, (base, total)

    fig, ax = plt.subplots(figsize=(W2, W2 * 0.40))
    bars = ax.bar(steps, heights, bottom=bottoms, color=cols, width=0.55)
    # 단계 사이 연결선: 각 단계 직후의 누적값 높이에 그린다
    running_after = [s['source_total']]
    for i in range(1, 4):
        running_after.append(running_after[-1] + deltas[i])
    running_after.append(total)
    assert running_after[3] == total, running_after
    for i in range(len(steps) - 1):
        ax.plot([i + 0.275, i + 1 - 0.275], [running_after[i]] * 2,
                color='#999999', lw=0.5, ls=':', zorder=0)
    for i, (b, h) in enumerate(zip(bottoms, heights)):
        val = deltas[i]
        txt = sgn(val) if val is not None else f'{h:,}'
        ax.annotate(txt, (i, b + h), ha='center', va='bottom', fontsize=6,
                    xytext=(0, 2), textcoords='offset points')
    ax.set_ylim(0, s['source_total'] * 1.12)
    ax.set_ylabel('L4 risk cards')
    ax.set_title(f"Card reconciliation: {s['source_total']} \u2212 {s['deleted']} \u2212 {s['merged_away']} + {s['split_net_addition']} = {total}")
    save(fig, FIG / 'cleaning_reconciliation.png')

    # 4. Retained mapping labels by domain ------------------------------------
    em = [sum(1 for c in cards if c['_domain'] == d and c['Mapping_Method'] == 'EM') for d in DOMAINS]
    hd = [sum(1 for c in cards if c['_domain'] == d and c['Mapping_Method'] == 'HD') for d in DOMAINS]
    fig, ax = plt.subplots(figsize=(W2, W2 * 0.42))
    ax.bar(SHORT, em, color=[DCOL[d] for d in DOMAINS], label=f'Retained EM label ({sum(em)})')
    ax.bar(SHORT, hd, bottom=em, color='#D4D7DC', edgecolor='#7A7A7A', lw=0.4,
           hatch='///', label=f'Retained HD decision ({sum(hd)})')
    for i, (e, h) in enumerate(zip(em, hd)):
        ax.annotate(str(e), (i, e / 2), ha='center', va='center', fontsize=6, color='white')
        ax.annotate(f'HD {h}', (i, e + h), ha='center', va='bottom', fontsize=6,
                    xytext=(0, 2), textcoords='offset points')
    add_global_mean(ax, [e + h for e, h in zip(em, hd)], 'h', label=f'Mean per domain ({total/3:.0f})')
    ax.set_ylabel('L4 risk cards')
    ax.set_title('Retained mapping labels by domain (no EM rerun in this release)')
    ax.legend(loc='upper right')
    save(fig, FIG / 'mapping_method_by_domain.png')

    # 5. Largest L3 categories per domain -------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(W2, W2 * 0.46),
                             gridspec_kw={'width_ratios': [1, 1, 1], 'wspace': 0.95})
    for ax, dom in zip(axes, DOMAINS):
        allc = Counter(c['L3_Title_en'] for c in cards if c['_domain'] == dom)
        cnt = allc.most_common(10)[::-1]
        names = [k for k, _ in cnt]; vals = [v for _, v in cnt]
        ax.barh(range(len(vals)), vals, color=DCOL[dom], height=0.70)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels([n if len(n) <= 31 else n[:30] + '\u2026' for n in names], fontsize=5)
        ax.set_xlim(0, max(vals) * 1.20)
        for i, v in enumerate(vals):
            ax.annotate(str(v), (v, i), va='center', ha='left', fontsize=5,
                        xytext=(2, 0), textcoords='offset points')
        allv = list(allc.values())
        add_global_mean(ax, allv, 'v', label=f'Mean {sum(allv)/len(allv):.1f}')
        ax.set_xlabel('L4 cards'); ax.set_title(dom, fontsize=7)
        ax.legend(loc='lower right', fontsize=5, borderaxespad=0.2)
    fig.suptitle(f'Largest L3 categories by domain (audited release, {total} cards)',
                 fontsize=8, y=1.02)
    save(fig, FIG / 'largest_l3_categories.png')

    # 6. Consolidation volume per audit correction ----------------------------
    traj = {a['step']: a['cards'] for a in manifest['audit_corrections']['card_count_trajectory']}
    order = ['AC-01', 'AC-02', 'AC-05', 'AC-06', 'AC-07', 'AC-08']
    prev = traj['round2_pipeline']; deltas = []
    for k in order:
        deltas.append(traj[k] - prev); prev = traj[k]
    fig, ax = plt.subplots(figsize=(W2, W2 * 0.38))
    bars = ax.bar(order, deltas, color=[NATURE_COLORS[2] if d > 0 else NATURE_COLORS[3] for d in deltas])
    for b, d in zip(bars, deltas):
        ax.annotate(sgn(d), (b.get_x() + b.get_width() / 2, b.get_height()), ha='center',
                    va='bottom' if d >= 0 else 'top', fontsize=6,
                    xytext=(0, 2 if d >= 0 else -2), textcoords='offset points')
    add_global_mean(ax, deltas, 'h', label=f'Mean net change ({MINUS}{abs(sum(deltas)/len(deltas)):.1f})')
    ax.axhline(0, color='#333333', lw=0.5)
    ax.set_ylim(min(deltas) * 1.30, max(deltas) + abs(min(deltas)) * 0.22)
    ax.set_ylabel('Net change in L4 cards')
    ax.set_title('Net card change per audit correction (two-reviewer consensus only)')
    ax.legend(loc='lower right')
    save(fig, FIG / 'audit_consolidation_by_correction.png')

    # 8. Round-2 approved reviewer actions (stage record) ---------------------
    acts = s['recovery_actions']
    keys = ['REMAP', 'REWRITE_KEEP', 'SPLIT', 'MERGE', 'DELETE']
    vals = [acts[k] for k in keys]
    fig, ax = plt.subplots(figsize=(W2 * 0.72, W2 * 0.34))
    bars = ax.bar([k.replace('_', '\n') for k in keys], vals, color=NATURE_COLORS[0])
    bar_labels(ax, bars)
    add_global_mean(ax, vals, 'h', label=f'Mean ({sum(vals)/len(vals):.1f})')
    ax.set_ylabel('Approved rows')
    ax.set_title('Round-2 approved reviewer actions (stage record, pre-audit)', fontsize=7)
    ax.legend(loc='upper right')
    save(fig, FIG / 'human_review_recovery_actions.png')

    # Table ------------------------------------------------------------------
    with (TAB / 'round2_domain_counts.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['Domain', 'Previous_release', 'Audited_release', 'Net_change',
                    'Retained_EM', 'Retained_HD'])
        for d, so, fi, e, h in zip(SHORT, source, final, em, hd):
            w.writerow([d, so, fi, fi - so, e, h])
        w.writerow(['Total', sum(source), total, total - sum(source), sum(em), sum(hd)])

    # Retire what cannot be rebuilt ------------------------------------------
    moved = []
    for name in RETIRE:
        src = FIG / name
        if src.exists():
            shutil.move(str(src), str(ARCH / name)); moved.append(name)
    (ARCH / 'README.md').write_text(
        '# Retired figures (pre-audit)\n\n'
        'These figures describe the pipeline before the line-by-line audit and cannot be '
        'rebuilt on the 629-card basis. Each depends on EM or Hybrid EM scores, on similarity '
        'scores, or on mapping score status. Those columns were removed from the release by '
        'AC-04 and AC-10, publishing score status was withdrawn by AC-12, and rerunning EM is '
        'not permitted. They are kept here as a record of the earlier rounds.\n\n'
        + ''.join(f'- `{k}` — {v}\n' for k, v in RETIRE.items()),
        encoding='utf-8')

    print(json.dumps({'cards': total, 'domains': dict(zip(SHORT, final)),
                      'em': sum(em), 'hd': sum(hd), 'retired': moved}, ensure_ascii=False))


if __name__ == '__main__':
    main()
