
import json, re
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
REL = 'v2.17.0'
OUT = ROOT / 'reports' / 'validation' / REL / 'hold_remap_bge'
OUT.mkdir(parents=True, exist_ok=True)
MODEL = Path('/Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181')
SEED = 20260721
np.random.seed(SEED)

cards = json.loads((ROOT/'public/data/releases'/REL/'cards.json').read_text())['cards']
hier = json.loads((ROOT/'public/data/releases'/REL/'hierarchy.json').read_text())['nodes']
l3nodes = [n for n in hier if n.get('level') == 3]
sem_l3 = [n for n in l3nodes if 'HLD' not in n['node_id']]
fam_ids = [n['node_id'] for n in sem_l3]
phys_fams = {f for f in fam_ids if f.startswith('RAI3-P')}
agentic_fams = {f for f in fam_ids if f.startswith('RAI3-A')}

hold_idx = [i for i,c in enumerate(cards) if 'HLD' in c.get('primary_l3_id','')]
assert len(hold_idx) == 734, len(hold_idx)

def card_text(c):
    return f'{c["label_en"]}. {c["definition_en"]} / {c.get("label_ko","")}. {c.get("definition_ko","")}'

def seed_text(n):
    return f'{n["label_en"]}. {n.get("definition_en","")} / {n.get("label_ko","")}. {n.get("definition_ko","")}'

def current_semantic_l3(c):
    h = c.get('hold_semantic_path') or {}
    return h.get('l3_id') or c.get('forced_candidate_l3_id') or c.get('previous_primary_l3_id')

texts = [card_text(c) for c in cards]
seeds = [seed_text(n) for n in sem_l3]
emb_path = OUT/'card_embeddings.npy'
seed_path = OUT/'l3_seed_embeddings.npy'
if emb_path.exists() and seed_path.exists():
    E = np.load(emb_path)
    S = np.load(seed_path)
else:
    m = SentenceTransformer(str(MODEL))
    try:
        m.max_seq_length = 256
    except Exception:
        pass
    E = m.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False).astype('float32')
    S = m.encode(seeds, normalize_embeddings=True, batch_size=32, show_progress_bar=False).astype('float32')
    np.save(emb_path, E)
    np.save(seed_path, S)

# keyword cosine
texts_en = [f'{c["label_en"]}. {c["definition_en"]}' for c in cards]
seeds_en = [f'{n["label_en"]}. {n.get("definition_en","")}' for n in sem_l3]
tv = TfidfVectorizer(lowercase=True, stop_words='english', max_features=20000)
X = tv.fit_transform(texts_en + seeds_en)
Xc = normalize(X[:len(cards)])
Xs = normalize(X[len(cards):])
W = (Xc @ Xs.T).toarray()
D = E @ S.T

AG_TERMS = re.compile(r'\b(agent|agentic|autonomous|tool[- ]?call|tool use|execution|planning|plans?\b|memory|multi-agent|orchestrat|self-improv|replicat|oversight)\b', re.I)
ag_ok = np.array([bool(AG_TERMS.search(t)) for t in texts_en])

proposals = []
score_rows = []
for i in hold_idx:
    c = cards[i]
    src = current_semantic_l3(c)
    src_i = fam_ids.index(src) if src in fam_ids else None
    # score uses direct seed similarity for HOLD-only reassignment, no released centroid reinforcement.
    score = 0.75 * D[i] + 0.25 * W[i]
    for k,fid in enumerate(fam_ids):
        if fid in phys_fams:
            score[k] = -999
        if fid in agentic_fams and not ag_ok[i]:
            score[k] = -999
    order = np.argsort(-score)
    best = int(order[0]); second = int(order[1])
    row = {
        'l4_id': c['l4_id'],
        'label_en': c['label_en'],
        'current_semantic_l3_id': src,
        'proposed_l3_id': fam_ids[best],
        'proposed_l3_label_en': sem_l3[best].get('label_en'),
        'score': round(float(score[best]), 6),
        'runner_up_l3_id': fam_ids[second],
        'runner_up_l3_label_en': sem_l3[second].get('label_en'),
        'margin': round(float(score[best] - score[second]), 6),
        'definition_cosine': round(float(D[i,best]), 6),
        'keyword_cosine': round(float(W[i,best]), 6),
        'changed_from_current': src != fam_ids[best],
        'decision_tier': 'strong' if (score[best] >= 0.72 and score[best]-score[second] >= 0.025 and W[i,best] >= 0.02) else 'moderate' if (score[best] >= 0.68 and score[best]-score[second] >= 0.010) else 'weak'
    }
    score_rows.append(row)
    if row['changed_from_current']:
        proposals.append(row)

summary = {
    'release_id': REL,
    'model': str(MODEL),
    'seed': SEED,
    'hold_cards': len(hold_idx),
    'changed_candidates': len(proposals),
    'tiers_all': {t: sum(1 for r in score_rows if r['decision_tier']==t) for t in ['strong','moderate','weak']},
    'tiers_changed': {t: sum(1 for r in proposals if r['decision_tier']==t) for t in ['strong','moderate','weak']},
}
(OUT/'hold_remap_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
(OUT/'hold_remap_all_scores.json').write_text(json.dumps(score_rows, ensure_ascii=False, indent=2))
(OUT/'hold_remap_changed_candidates.json').write_text(json.dumps(proposals, ensure_ascii=False, indent=2))
print(json.dumps(summary, ensure_ascii=False, indent=2))
print('OUT', OUT)
