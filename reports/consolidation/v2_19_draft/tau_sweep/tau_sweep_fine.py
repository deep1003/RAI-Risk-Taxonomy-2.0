import json, numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from collections import Counter

cards = json.load(open('public/data/releases/v2.18.0-rc/cards.json'))['cards']
act = [c for c in cards if c['status']=='active']
ids = [c['l4_id'] for c in act]
print('active', len(act))

E = np.load('reports/validation/v2.17.2/full_mapping_sensitivity_bge_m3_20260724/card_embeddings.npy')
E2 = np.load('reports/consolidation/simulation/embeddings_bge-m3_1660.npy')
En = E/np.linalg.norm(E,axis=1,keepdims=True)
E2n = E2/np.linalg.norm(E2,axis=1,keepdims=True)
print('canonical vs sim mean abs diff', np.abs((En*E2n).sum(1)-1).mean())

S = En@En.T
np.fill_diagonal(S,1.0)
D = np.clip(1-S,0,None); np.fill_diagonal(D,0)
Z = linkage(squareform(D,checks=False), method='complete')

l3 = {c['l4_id']: c.get('primary_l3_id') for c in act}
br = {}
for c in act:
    b = c.get('breadcrumb') or []
    l1 = next((n['node_id'] for n in b if n['node_id'].startswith('RAI1')), None)
    br[c['l4_id']] = l1

dnm = [("RAI4-0228","RAI4-0229"),("RAI4-0659","RAI4-0892"),("RAI4-0863","RAI4-0870"),("RAI4-0682","RAI4-0691")]
plan = json.load(open('reports/consolidation/v2_19_draft/v2_19_merge_plan.json'))
pos = []
for m in plan['merges']:
    s = m['source_l4_ids']
    for i in range(len(s)):
        for j in range(i+1,len(s)):
            pos.append((s[i],s[j]))
idx = {k:i for i,k in enumerate(ids)}

rows=[]
for tau in [round(x,3) for x in np.arange(0.60,0.991,0.01)]:
    lab = fcluster(Z, t=1-tau, criterion='distance')
    cnt = Counter(lab)
    n = len(cnt)
    multi = sum(1 for v in cnt.values() if v>1)
    single = n-multi
    largest = max(cnt.values())
    groups={}
    for i,g in enumerate(lab): groups.setdefault(g,[]).append(ids[i])
    crossL3 = sum(1 for g,v in groups.items() if len(v)>1 and len({l3[x] for x in v})>1)
    crossL1 = sum(1 for g,v in groups.items() if len(v)>1 and len({br[x] for x in v})>1)
    viol = sum(1 for a,b in dnm if a in idx and b in idx and lab[idx[a]]==lab[idx[b]])
    hit  = sum(1 for a,b in pos if a in idx and b in idx and lab[idx[a]]==lab[idx[b]])
    rows.append(dict(tau=tau,n_cards=n,reduction=len(ids)-n,pct=round(100*(len(ids)-n)/len(ids),1),
                     multi=multi,singleton=single,largest=largest,crossL3=crossL3,crossL1=crossL1,
                     dnm_violations=viol,golden_pos_captured=f"{hit}/{len(pos)}"))
json.dump(rows, open('/tmp/sweep.json','w'), indent=1)
hdr = f"{'tau':>5} {'cards':>6} {'감축':>6} {'%':>6} {'multi':>6} {'single':>7} {'max':>4} {'xL3':>5} {'xL1':>5} {'DNM위반':>7} {'golden':>7}"
print(hdr); print('-'*len(hdr))
for r in rows:
    print(f"{r['tau']:>5} {r['n_cards']:>6} {r['reduction']:>6} {r['pct']:>6} {r['multi']:>6} {r['singleton']:>7} {r['largest']:>4} {r['crossL3']:>5} {r['crossL1']:>5} {r['dnm_violations']:>7} {r['golden_pos_captured']:>7}")
