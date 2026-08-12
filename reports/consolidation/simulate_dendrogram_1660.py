#!/usr/bin/env python3
"""Multi-resolution dendrogram simulation over all 1,660 active L4 cards.
Embeds bilingual card text with BGE-M3 (ollama), builds full pairwise cosine
matrix, then cuts complete-linkage and average-linkage dendrograms at
tau in {0.94, 0.88, 0.82, 0.76, 0.70}. Also reports single-linkage for contrast.
Outputs: embeddings npy, level assignments CSV, summary JSON."""
import json, time, urllib.request, csv
import numpy as np
from pathlib import Path

BASE = Path('/Users/deep1003/data3/RAI-Risk-Taxonomy')
OUT = BASE / 'reports/consolidation/simulation'
OUT.mkdir(parents=True, exist_ok=True)
REL = BASE / 'public/data/releases/v2.18.0-rc/cards.json'

cards = [c for c in json.load(open(REL))['cards'] if c['status'] == 'active']
print('active cards:', len(cards))

def card_text(c):
    parts = [c.get('label_en') or '', c.get('label_ko') or '',
             c.get('definition_en') or '', c.get('definition_ko') or '']
    return ' :: '.join(p for p in parts if p)

texts = [card_text(c) for c in cards]

EMB = OUT / 'embeddings_bge-m3_1660.npy'
if EMB.exists():
    E = np.load(EMB)
    print('loaded cached embeddings', E.shape)
else:
    vecs = []
    t0 = time.time()
    for k, t in enumerate(texts):
        req = urllib.request.Request('http://localhost:11434/api/embeddings',
            data=json.dumps({'model': 'bge-m3', 'prompt': t}).encode(),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            vecs.append(json.load(r)['embedding'])
        if (k + 1) % 200 == 0:
            print(f'{k+1}/{len(texts)}  {time.time()-t0:.0f}s', flush=True)
    E = np.asarray(vecs, dtype=np.float32)
    np.save(EMB, E)
    print('embedded', E.shape, f'{time.time()-t0:.0f}s')

E = E / np.linalg.norm(E, axis=1, keepdims=True)
S = E @ E.T
D = 1 - S
np.fill_diagonal(D, 0)
D[D < 0] = 0

import scipy.cluster.hierarchy as h
from scipy.spatial.distance import squareform
cond = squareform(D, checks=False)

def L1(c):
    b = c.get('breadcrumb') or []
    return b[1]['node_id'] if len(b) > 1 else None

LEVELS = [0.94, 0.88, 0.82, 0.76, 0.70]
summary = {}
assign = {c['l4_id']: {} for c in cards}

for method in ('complete', 'average', 'single'):
    Z = h.linkage(cond, method=method)
    summary[method] = {}
    for tau in LEVELS:
        lab = h.fcluster(Z, t=1 - tau, criterion='distance')
        groups = {}
        for i, l in enumerate(lab):
            groups.setdefault(int(l), []).append(i)
        sizes = sorted((len(v) for v in groups.values()), reverse=True)
        multi = [v for v in groups.values() if len(v) > 1]
        crossL1 = sum(1 for v in multi if len({L1(cards[i]) for i in v}) > 1)
        physmix = sum(1 for v in multi
                      if any(L1(cards[i]) == 'RAI1-P' for i in v)
                      and any(L1(cards[i]) != 'RAI1-P' for i in v))
        summary[method][tau] = {
            'n_clusters': len(groups), 'cards_after_merge': len(groups),
            'reduction': len(cards) - len(groups),
            'largest': sizes[0], 'top5_sizes': sizes[:5],
            'multi_groups': len(multi), 'crossL1_groups': crossL1,
            'physical_mixed_groups': physmix,
        }
        if method == 'complete':
            for i, l in enumerate(lab):
                assign[cards[i]['l4_id']][f'tau_{tau}'] = int(l)
        print(f"{method:8s} tau={tau:.2f}  clusters={len(groups):4d}  "
              f"largest={sizes[0]:4d}  crossL1={crossL1:3d}  physmix={physmix:3d}")

# example coarse clusters at 0.70 (complete linkage)
Zc = h.linkage(cond, method='complete')
lab70 = h.fcluster(Zc, t=0.30, criterion='distance')
g70 = {}
for i, l in enumerate(lab70):
    g70.setdefault(int(l), []).append(i)
big = sorted(g70.items(), key=lambda kv: -len(kv[1]))[:8]
examples = []
for gid, idxs in big:
    l1c = {}
    for i in idxs:
        l1c[L1(cards[i])] = l1c.get(L1(cards[i]), 0) + 1
    labels = [cards[i]['label_en'][:44] for i in idxs[:5]]
    examples.append({'cluster': gid, 'size': len(idxs), 'l1_mix': l1c, 'sample_labels': labels})
    print(f"[0.70 cluster {gid}] n={len(idxs)} l1={l1c}")
    for s in labels:
        print('   -', s)

json.dump({'summary': summary, 'coarse_examples': examples},
          open(OUT / 'dendrogram_summary.json', 'w'), ensure_ascii=False, indent=2)
with open(OUT / 'level_assignments_complete.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['l4_id', 'label_en', 'L1'] + [f'tau_{t}' for t in LEVELS])
    for c in cards:
        w.writerow([c['l4_id'], c['label_en'], L1(c)] +
                   [assign[c['l4_id']][f'tau_{t}'] for t in LEVELS])
print('DONE ->', OUT)
