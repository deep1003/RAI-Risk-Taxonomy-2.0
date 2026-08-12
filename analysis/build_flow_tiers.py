# build_flow_tiers.py — derive granularity-flow tiers F2, F3 and F5 from the released states
# Each tier is obtained by merging the previous tier's representatives at the crossing
# boundary of that consolidation step, using the medoid rule of flow_canonical.py.
# L3 labels propagate from the representative of the merge group.
import json, numpy as np

REV = 'data/experiments/review'
emb = np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X = emb / np.linalg.norm(emb, axis=1, keepdims=True)
master = json.load(open('data/experiments/stage1/out/master.json'))['cards']
pos = {c['l4_id']: i for i, c in enumerate(master)}
STEPS = json.load(open(f'{REV}/flow_states.json'))['steps']


def consolidate(cards, tau):
    """Merge the given tier's representatives at tau; return the next tier's cards."""
    alive = [pos[c['rep']] for c in cards]
    n = len(alive)
    A = X[alive]
    S = (A @ A.T).astype(np.float32)
    np.fill_diagonal(S, -1)

    parent = np.arange(n)
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    ii, jj = np.where(np.triu(S, 1) >= tau)
    for a, b in zip(ii, jj):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb: parent[rb] = ra
    lab = np.array([find(i) for i in range(n)])

    out = []
    for r in sorted(set(lab.tolist())):
        loc = np.where(lab == r)[0]
        src = [cards[i] for i in loc]
        if len(loc) == 1:
            keep = src[0]
        else:
            sub = S[np.ix_(loc, loc)]
            keep = src[int(np.argmax(sub.mean(1)))]
        members = [m for c in src for m in c['members']]
        mp = [pos[m] for m in members]
        if len(mp) > 1:
            Ssub = X[mp] @ X[mp].T
            mn = float(Ssub[np.triu_indices(len(mp), 1)].min())
        else:
            mn = None
        l3s = {c['l3'] for c in src}
        out.append(dict(rep=keep['rep'], n=len(members), min_cos=mn, members=members,
                        l3=keep['l3'],
                        l3_conflict=(len(l3s) > 1 or any(c.get('l3_conflict') for c in src)),
                        label_ko=keep['label_ko'], label_en=keep['label_en'],
                        definition_ko=keep['definition_ko'], definition_en=keep['definition_en'],
                        refined=False, l3_majority=keep.get('l3_majority'),
                        em_margin=keep.get('em_margin'), em_status=keep.get('em_status'),
                        prev_groups=len(loc)))
    return out


SOC_SCOPE = {}
with open(f'{REV}/master_soc_scope_mapping.csv', encoding='utf-8') as fh:
    next(fh)
    for line in fh:
        p = line.rstrip('\n').split(',')
        if len(p) >= 5: SOC_SCOPE[p[0]] = p[3]


def family(card):
    """L1 family, honouring the Societal Safety scope split (G / A / P)."""
    l3 = card['l3']
    if '-SOC-' in l3:
        l3 = SOC_SCOPE.get(card['rep'], l3)
    return l3.split('-')[1]


def domains(cards):
    from collections import Counter
    c = Counter(family(x) for x in cards)
    return f"{c['G']} / {c['A']} / {c['P']}"


N0 = len(master)
# Master domain counts: the EM assignment of the canonical inventory, with the
# Societal Safety axis routed by scope (its 430 cards split 351 / 37 / 42).
MASTER_DOM = (1233 - 37 - 42, 118 + 37, 261 + 42)
rows = [('Master', None, N0, None, None, '%d / %d / %d' % MASTER_DOM)]

F1 = json.load(open(f'{REV}/f1_state.json'))['cards']
rows.append(('F1', STEPS[0]['tau'], len(F1), STEPS[0]['groups'], N0 - len(F1), domains(F1)))

# F2, F3 derived from F1; F4 is the audited state on disk; F5 derived from F4.
F2 = consolidate(F1, STEPS[1]['tau'])
F3 = consolidate(F2, STEPS[2]['tau'])
F4 = json.load(open(f'{REV}/flow4_cards_full.json'))['cards']
F5 = consolidate(F4, STEPS[4]['tau'])

for name, cards, step in (('F2', F2, 1), ('F3', F3, 2), ('F4', F4, 3), ('F5', F5, 4)):
    rows.append((name, STEPS[step]['tau'], len(cards), STEPS[step]['groups'],
                 N0 - len(cards), domains(cards)))

for name, cards in (('f2', F2), ('f3', F3), ('f5', F5)):
    json.dump(dict(taus=[s['tau'] for s in STEPS[:int(name[1])]], cards=cards),
              open(f'{REV}/{name}_state.json', 'w'), ensure_ascii=False, indent=1)

w = (8, 8, 7, 14, 10, 20)
hdr = ('Tier', 'tau*', 'Cards', 'Merge groups', 'Absorbed', 'G / A / P')
print(''.join(h.ljust(x) for h, x in zip(hdr, w)))
for r in rows:
    cells = [r[0],
             '-' if r[1] is None else f'{r[1]:.4f}',
             f'{r[2]:,}',
             '-' if r[3] is None else str(r[3]),
             '-' if r[4] is None else f'{r[4]:,}',
             r[5] or '-']
    print(''.join(c.ljust(x) for c, x in zip(cells, w)))
