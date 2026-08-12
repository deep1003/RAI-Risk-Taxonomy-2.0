# top_pairs.py — highest-similarity card pairs in each source inventory
import json, numpy as np

def top10(X, texts, ids):
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    S = Xn @ Xn.T
    np.fill_diagonal(S, -1)
    iu = np.triu_indices(len(ids), 1)
    v = S[iu]
    order = np.argsort(-v)[:10]
    return [(ids[iu[0][k]], texts[iu[0][k]], ids[iu[1][k]], texts[iu[1][k]], float(v[k]))
            for k in order]

out = {}

emb = np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
cards = json.load(open('data/experiments/stage1/out/master.json'))['cards']
out['ours'] = top10(emb, [(c.get('label_en') or c.get('label_ko') or '') for c in cards],
                    [c['l4_id'] for c in cards])

E = np.load('data/experiments/mit_replication/emb_mit_bge.npy')
items = json.load(open('data/experiments/mit_replication/mit_risks.json'))
def mit_label(it):
    t = (it['subcategory'] or it['category'] or '').strip()
    return '' if t in ('-', '--', 'n/a', 'N/A') else t
keep = [i for i, it in enumerate(items) if mit_label(items[i])]
labels = [mit_label(items[i]) for i in keep]
qids = [items[i].get('quickref', '') for i in keep]
out['mit'] = top10(E[keep], labels, qids)
out['mit_n'] = len(keep)
out['mit_exact_dupes'] = sum(1 for a, at, b, bt, c in out['mit'] if at == bt)

json.dump(out, open('data/experiments/review/top_pairs.json', 'w'), ensure_ascii=False, indent=1)
for k, v in [(k, v) for k, v in out.items() if isinstance(v, list)]:
    print('==', k)
    for a, at, b, bt, c in v:
        print(f'  {c:.4f}  {a} {at[:46]!r}  ||  {b} {bt[:46]!r}')
