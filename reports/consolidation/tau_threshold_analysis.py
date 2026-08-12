#!/usr/bin/env python3
"""Determine the over-merge (too-low tau) and under-merge (too-high tau) thresholds
empirically, using the canonical embeddings and the two-reviewer golden set.

Golden positives  = card pairs that SHOULD merge (8 approved merge groups)
Golden negatives  = card pairs that should NOT merge (do-not-merge list: distinct
                    constructs and embedding false positives adjudicated by reviewers)

For each tau, a pair (i,j) is 'predicted merge' iff complete-linkage assigns them to
the same cluster at cut level tau. We compute precision, recall, F1 on the golden
pairs, plus the number of predicted merges and cross-L3 merges, and locate:
  - tau_under : highest tau at which recall of true merges is still < 1 (above it we miss real duplicates)
  - tau_over  : lowest tau at which precision drops (below it we start merging things that should stay apart)
Outputs a figure and a JSON summary. Reads canonical embeddings only; writes to
reports/consolidation/simulation/.
"""
import json
import numpy as np
from pathlib import Path
import scipy.cluster.hierarchy as h
from scipy.spatial.distance import squareform

BASE = Path('/Users/deep1003/data3/RAI-Risk-Taxonomy')
CANON = BASE / 'reports/validation/v2.17.2/full_mapping_sensitivity_bge_m3_20260724'
OUT = BASE / 'reports/consolidation/simulation'
REL = BASE / 'public/data/releases/v2.18.0-rc/cards.json'

cards = [c for c in json.load(open(REL))['cards'] if c['status'] == 'active']
ids = [c['l4_id'] for c in cards]
pos = {k: i for i, k in enumerate(ids)}
l3 = {c['l4_id']: c.get('primary_l3_id') for c in cards}

# canonical embeddings, aligned to active-card order
ids_c = json.load(open(CANON / 'index.json'))['l4_ids']
posc = {k: i for i, k in enumerate(ids_c)}
E = np.load(CANON / 'card_embeddings.npy').astype(np.float64)[[posc[k] for k in ids]]
E = E / np.linalg.norm(E, axis=1, keepdims=True)
D = 1 - E @ E.T
np.fill_diagonal(D, 0); D[D < 0] = 0
Z = h.linkage(squareform(D, checks=False), method='complete')

# ---- golden set from reviewer adjudication ----
R = json.load(open(OUT / 'reviewed_cards_final.json'))
pos_pairs, neg_pairs = [], []
for o in R['reviewed_cards']:
    members = [str(m).split(' ')[0] for m in o['members']]
    members = [m for m in members if m in pos]
    if len(members) < 2:
        continue
    pair = (pos[members[0]], pos[members[1]])
    if o['final'] == 'approved':
        pos_pairs.append(pair)      # should merge
    else:
        neg_pairs.append(pair)      # should NOT merge (rejected / defer)
# additional hard negatives from the do-not-merge corruption/false-positive list
DNM = [('RAI4-0228','RAI4-0229'), ('RAI4-0659','RAI4-0892'),
       ('RAI4-0863','RAI4-0870'), ('RAI4-0682','RAI4-0691')]
for a, b in DNM:
    if a in pos and b in pos and (pos[a], pos[b]) not in neg_pairs and (pos[b], pos[a]) not in neg_pairs:
        neg_pairs.append((pos[a], pos[b]))
print(f'golden positives (should merge): {len(pos_pairs)}')
print(f'golden negatives (should not merge): {len(neg_pairs)}')

def same_cluster(tau, pair):
    lab = h.fcluster(Z, t=1 - tau, criterion='distance')
    return lab[pair[0]] == lab[pair[1]]

def cosine(pair):
    return float(E[pair[0]] @ E[pair[1]])

print('\ngolden positive pair cosines:', sorted(round(cosine(p),3) for p in pos_pairs))
print('golden negative pair cosines:', sorted(round(cosine(p),3) for p in neg_pairs))

taus = np.round(np.arange(0.99, 0.599, -0.01), 2)
rows = []
for tau in taus:
    lab = h.fcluster(Z, t=1 - tau, criterion='distance')
    tp = sum(1 for p in pos_pairs if lab[p[0]] == lab[p[1]])
    fn = len(pos_pairs) - tp
    fp = sum(1 for p in neg_pairs if lab[p[0]] == lab[p[1]])
    tn = len(neg_pairs) - fp
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    groups = {}
    for i, l in enumerate(lab):
        groups.setdefault(int(l), []).append(i)
    merged = sum(len(v) - 1 for v in groups.values() if len(v) > 1)
    crossL3 = sum(1 for v in groups.values() if len(v) > 1 and len({l3[ids[i]] for i in v}) > 1)
    rows.append(dict(tau=float(tau), precision=prec, recall=rec, f1=f1,
                     tp=tp, fp=fp, fn=fn, merged=merged, crossL3=crossL3))

# thresholds
recall1 = [r['tau'] for r in rows if r['recall'] >= 0.999]
tau_under = max(recall1) if recall1 else None          # at/above this we still capture all true merges; just above the first miss
first_miss = min([r['tau'] for r in rows if r['recall'] < 0.999], default=None)
prec1 = [r['tau'] for r in rows if r['precision'] >= 0.999]
tau_over = min(prec1) if prec1 else None                # lowest tau with precision still 1; below it precision breaks
first_fp = max([r['tau'] for r in rows if r['precision'] < 0.999], default=None)
best_f1 = max(rows, key=lambda r: (r['f1'], r['tau']))

print(f"\n=== thresholds ===")
print(f"under-merge boundary: tau >= {tau_under}  (recall of true merges = 1.0 down to here; first miss at tau={first_miss})")
print(f"  → tau가 이 값보다 높으면 실제 중복을 놓치는 과소병합(under-merge)")
print(f"over-merge boundary : tau <= {tau_over}  (precision still 1.0 down to here; first false merge at tau={first_fp})")
print(f"  → tau가 이 값보다 낮으면 분리해야 할 쌍을 합치는 과대병합(over-merge)")
print(f"safe operating band : {first_fp if first_fp else 0.60} < tau <= {tau_under}   (best F1 at tau={best_f1['tau']}, F1={best_f1['f1']:.2f})")

summary = dict(golden_positives=len(pos_pairs), golden_negatives=len(neg_pairs),
               tau_under_merge_above=tau_under, first_missed_true_merge_at=first_miss,
               tau_over_merge_below=tau_over, first_false_merge_at=first_fp,
               best_f1_tau=best_f1['tau'], rows=rows)
json.dump(summary, open(OUT / 'tau_threshold_analysis.json', 'w'), ensure_ascii=False, indent=2)

# ---- figure ----
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': 'Arial', 'font.size': 9})
T = [r['tau'] for r in rows]
fig, ax = plt.subplots(figsize=(9.2, 5.0))
ax.plot(T, [r['recall'] for r in rows], 'o-', color='#1f5fa8', label='recall (true merges captured)')
ax.plot(T, [r['precision'] for r in rows], 's-', color='#e07a5f', label='precision (merges that are correct)')
ax.plot(T, [r['f1'] for r in rows], '^-', color='#14532d', label='F1')
if tau_under: ax.axvline(tau_under, color='#1f5fa8', ls='--', lw=1.2)
if first_fp: ax.axvspan(0.595, first_fp, color='#e07a5f', alpha=0.08)
if tau_under: ax.axvspan(tau_under, 0.995, color='#9aa0a6', alpha=0.10)
ax.set_xlabel('tau (merge threshold)'); ax.set_ylabel('score'); ax.set_ylim(-0.03, 1.05)
ax.invert_xaxis(); ax.grid(alpha=0.3); ax.legend(loc='center left', fontsize=8)
band_txt = f"under-merge  tau > {tau_under}" if tau_under else ''
over_txt = f"over-merge  tau < {first_fp}" if first_fp else ''
ax.set_title(f"tau validity against reviewer golden set  ({over_txt}  |  safe band  |  {band_txt})")
# annotate boundaries
if tau_under:
    ax.annotate('under-merge\n(misses real duplicates)', xy=(tau_under, 0.5),
                xytext=(tau_under+0.03, 0.35), fontsize=8, color='#5b6b7a',
                arrowprops=dict(arrowstyle='->', color='#9aa0a6'))
if first_fp:
    ax.annotate('over-merge\n(merges distinct risks)', xy=(first_fp, 0.5),
                xytext=(first_fp-0.10, 0.30), fontsize=8, color='#7c2d12',
                arrowprops=dict(arrowstyle='->', color='#e07a5f'))
fig.tight_layout()
fig.savefig(OUT / 'fig_tau_over_under_merge.png', dpi=200)
print('\nsaved -> fig_tau_over_under_merge.png, tau_threshold_analysis.json')
