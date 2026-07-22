import json, sys, os, numpy as np, re, hashlib
from pathlib import Path
MODEL = sys.argv[1] if len(sys.argv)>1 else "intfloat/multilingual-e5-small"
TAG = "bge" if "bge" in MODEL else "e5"
RELEASE_ID = sys.argv[2] if len(sys.argv)>2 else "v2.17.0"
SEED = 20260721
np.random.seed(SEED)
BASE = str(Path(__file__).resolve().parents[1])
OUT = f"{BASE}/reports/validation/{RELEASE_ID}/audit_{TAG}"
os.makedirs(OUT, exist_ok=True)
cards = json.load(open(f"{BASE}/public/data/releases/{RELEASE_ID}/cards.json"))["cards"]
hier = json.load(open(f"{BASE}/public/data/releases/{RELEASE_ID}/hierarchy.json"))
l3nodes = [n for n in hier["nodes"] if n.get("level")==3]
sem_l3 = [n for n in l3nodes if "HLD" not in n["node_id"]]
assert len(sem_l3)==50, len(sem_l3)
fam_ids = [n["node_id"] for n in sem_l3]
fam_idx = {f:i for i,f in enumerate(fam_ids)}
phys_fams = set(f for f in fam_ids if f.startswith("RAI3-P"))
agentic_fams = set(f for f in fam_ids if f.startswith("RAI3-A"))
def card_text(c):
    return f'{c["label_en"]}. {c["definition_en"]} / {c["label_ko"]}. {c["definition_ko"]}'
def seed_text(n):
    return f'{n["label_en"]}. {n.get("definition_en","")} / {n.get("label_ko","")}. {n.get("definition_ko","")}'
def cur_l3(c):
    if "HLD" in c["primary_l3_id"]:
        return c["hold_semantic_path"]["l3_id"]
    return c["primary_l3_id"]
texts = [card_text(c) for c in cards]
seeds = [seed_text(n) for n in sem_l3]
# ---- embeddings with checkpoint
emb_path = f"{OUT}/card_embeddings.npy"; seed_path = f"{OUT}/l3_seed_embeddings.npy"
if os.path.exists(emb_path) and os.path.exists(seed_path):
    E = np.load(emb_path); S = np.load(seed_path)
else:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL)
    try: m.max_seq_length = 256
    except Exception: pass
    pre = "passage: " if TAG=="e5" else ""
    E = m.encode([pre+t for t in texts], normalize_embeddings=True, batch_size=32, show_progress_bar=False).astype("float32")
    S = m.encode([pre+t for t in seeds], normalize_embeddings=True, batch_size=32, show_progress_bar=False).astype("float32")
    np.save(emb_path, E); np.save(seed_path, S)
print("emb", E.shape, "seeds", S.shape, flush=True)
N = len(cards)
cur = np.array([fam_idx[cur_l3(c)] for c in cards])
is_phys_card = np.array([c["primary_l3_id"].startswith("RAI3-P") for c in cards])
is_hold = np.array(["HLD" in c["primary_l3_id"] for c in cards])
# ---- TF-IDF keyword cosine (English side)
from sklearn.feature_extraction.text import TfidfVectorizer
en_texts = [f'{c["label_en"]}. {c["definition_en"]}' for c in cards]
en_seeds = [f'{n["label_en"]}. {n.get("definition_en","")}' for n in sem_l3]
tv = TfidfVectorizer(lowercase=True, stop_words="english", max_features=20000)
X = tv.fit_transform(en_texts + en_seeds)
Xc = X[:N]; Xs = X[N:]
from sklearn.preprocessing import normalize
Xc = normalize(Xc); Xs = normalize(Xs)
W = (Xc @ Xs.T).toarray()  # keyword cosine card x fam
D = E @ S.T                # definition cosine card x fam
AG_TERMS = re.compile(r"\b(agent|agentic|autonomous|tool[- ]?call|tool use|execution|planning|plans?\b|memory|multi-agent|orchestrat|self-improv|replicat|oversight)\b", re.I)
ag_ok = np.array([bool(AG_TERMS.search(t)) for t in en_texts])
# ---- constrained EM audit (TR section 3.7)
ap = f"{OUT}/final_assignment.npy"
if os.path.exists(ap):
    assign = np.load(ap); moves_log = json.load(open(f"{OUT}/reassignment_proposals.json")); skip_audit = True
else:
    assign = cur.copy(); moves_log = []; skip_audit = False
for it in range(10):
    if skip_audit: break
    C = np.zeros((50, E.shape[1]), dtype="float32")
    for k in range(50):
        mem = E[assign==k]
        C[k] = mem.mean(0) if len(mem) else S[k]
        n_ = np.linalg.norm(C[k]);  C[k] = C[k]/n_ if n_>0 else C[k]
    Sc = 0.60*(E@C.T) + 0.30*D + 0.10*W
    # mask: physical cards fixed; physical destinations excluded for non-physical
    changed = 0
    for i in range(N):
        if is_phys_card[i]: continue
        srcS = Sc[i, assign[i]]
        order = np.argsort(-Sc[i])
        for k in order:
            if fam_ids[k] in phys_fams: continue
            if k == assign[i]: break
            if fam_ids[k] in agentic_fams and not ag_ok[i]: continue
            if Sc[i,k] - srcS >= 0.020 and W[i,k] >= 0.015 and D[i,k] >= D[i, assign[i]]:
                moves_log.append({"l4_id":cards[i]["l4_id"],"iter":it,"from":fam_ids[assign[i]],"to":fam_ids[k],
                                  "S_from":float(srcS),"S_to":float(Sc[i,k]),"improvement":float(Sc[i,k]-srcS),
                                  "keyword_cos":float(W[i,k]),"def_cos_to":float(D[i,k]),"def_cos_from":float(D[i,assign[i]])})
                assign[i] = k; changed += 1
            break
    print("iter", it, "moves", changed, flush=True)
    if changed == 0: break
if not skip_audit:
    json.dump(moves_log, open(f"{OUT}/reassignment_proposals.json","w"), ensure_ascii=False, indent=1)
uniq_moved = sorted(set(m["l4_id"] for m in moves_log))
print("total move events", len(moves_log), "unique cards moved", len(uniq_moved), flush=True)
np.save(f"{OUT}/final_assignment.npy", assign)
json.dump({"fam_ids":fam_ids,"l4_ids":[c["l4_id"] for c in cards]}, open(f"{OUT}/index.json","w"))
# ---- reliability function
def reliability(mask, label, part):
    idx = np.where(mask)[0]
    Em = E[idx]; pm = part[idx]
    res = {"condition":label,"cards":int(len(idx))}
    C = np.zeros((50, E.shape[1]), dtype="float32"); sizes = np.zeros(50, int)
    for k in range(50):
        mem = Em[pm==k]; sizes[k]=len(mem)
        C[k] = mem.mean(0) if len(mem) else S[k]
        n_=np.linalg.norm(C[k]); C[k]=C[k]/n_ if n_>0 else C[k]
    sims = Em @ C.T
    ranks = np.argsort(-sims, axis=1)
    pos = (ranks == pm[:,None]).argmax(1)
    for k_ in (1,2,3,5):
        res[f"top{k_}_containment"] = round(float((pos < k_).mean())*100,1)
    top1 = sims.argmax(1); srt = np.sort(sims,axis=1)
    res["median_margin"] = round(float(np.median(sims[np.arange(len(idx)),pm] - np.where(top1==pm, srt[:,-2], srt[:,-1]))),4)
    res["negative_margin_share"] = round(float(((sims[np.arange(len(idx)),pm] - np.where(top1==pm, srt[:,-2], srt[:,-1]))<0).mean())*100,1)
    # within-family cosine + permutation
    def cohesion(p):
        tot=0.0; cnt=0
        for k in range(50):
            mem = Em[p==k]
            if len(mem)>=2:
                c_=mem.mean(0); c_/=np.linalg.norm(c_)
                tot += float((mem@c_).sum()); cnt += len(mem)
        return tot/cnt if cnt else 0.0
    obs = cohesion(pm)
    rng = np.random.default_rng(SEED)
    null = np.array([cohesion(rng.permutation(pm)) for _ in range(5000)])
    res["mean_within_family_cosine"] = round(obs,4)
    res["null_mean"] = round(float(null.mean()),4)
    res["permutation_p"] = round(float((1+(null>=obs).sum())/(len(null)+1)),4)
    # EM from seeds
    z = (Em @ S.T).argmax(1); obj_prev=-1
    for t in range(60):
        Cz = np.zeros_like(C)
        for k in range(50):
            mem=Em[z==k]
            Cz[k]=mem.mean(0) if len(mem) else S[k]
            n_=np.linalg.norm(Cz[k]); Cz[k]=Cz[k]/n_ if n_>0 else Cz[k]
        z2=(Em@Cz.T).argmax(1)
        obj=float((Em@Cz.T).max(1).mean())
        if (z2==z).all(): z=z2; break
        z=z2
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    res["em_iterations"]=t+1; res["em_final_objective"]=round(obj,3)
    res["em_agreement"]=round(float((z==pm).mean())*100,1)
    res["ari"]=round(adjusted_rand_score(pm,z),3); res["nmi"]=round(normalized_mutual_info_score(pm,z),3)
    # perturbation
    rng = np.random.default_rng(SEED)
    for sig in (0.01,0.05):
        agree=[]
        for rep in range(200):
            Ep = Em + rng.normal(0,sig,Em.shape).astype("float32")
            Ep /= np.linalg.norm(Ep,axis=1,keepdims=True)
            agree.append(float(((Ep@C.T).argmax(1)==top1).mean()))
        res[f"perturb_agreement_sigma_{sig}"]=round(float(np.mean(agree))*100,1)
    return res
results = {"model":MODEL,"seed":SEED,"release":RELEASE_ID,
 "baseline_pre_audit": None, "post_audit": None}
allmask = np.ones(N,bool)
nonhold = ~is_hold
def cached(name, fn):
    p = f"{OUT}/rel_{name}.json"
    if os.path.exists(p): return json.load(open(p))
    r = fn(); json.dump(r, open(p,"w"), indent=1); print("saved", name, flush=True); return r
results["baseline_pre_audit"] = {"all": cached("all_pre", lambda: reliability(allmask,"all_pre",cur)),
 "non_hold": cached("nonhold_pre", lambda: reliability(nonhold,"nonhold_pre",cur))}
results["post_audit"] = {"all": cached("all_post", lambda: reliability(allmask,"all_post",assign)),
 "non_hold": cached("nonhold_post", lambda: reliability(nonhold,"nonhold_post",assign))}
json.dump(results, open(f"{OUT}/reliability_results.json","w"), indent=1)
print(json.dumps(results["post_audit"]["all"], indent=1)[:600])
print("PIPELINE_DONE")
