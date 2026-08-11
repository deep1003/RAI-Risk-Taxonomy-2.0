# Size-dependence test: cohesion vs nearest-cluster attraction sweep at variable subsample fraction
# usage: python3 tmp/coh_div_sweep_frac.py <frac> <n_reps> <suffix> [seed_base]
import numpy as np, sys, collections
frac = float(sys.argv[1]); nrep = int(sys.argv[2]); suf = sys.argv[3]
seed_base = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
emb = np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X = emb / np.linalg.norm(emb, axis=1, keepdims=True)
Sfull = (X @ X.T).astype(np.float32); N = Sfull.shape[0]
taus = np.round(np.arange(0.9400, 0.49999, -0.0001), 4)
ckset = set(range(0, len(taus), 20))  # 0.002-step checkpoints for Snn
K = 96

def sweep(idx):
    S = Sfull[np.ix_(idx, idx)]; n = len(idx)
    kk = min(K + 1, n - 1)
    part = np.argpartition(-S, kk, axis=1)[:, :kk + 1]
    rowv = np.take_along_axis(S, part, axis=1)
    ordr = np.argsort(-rowv, axis=1)
    NB = np.take_along_axis(part, ordr, axis=1)
    NBs = np.take_along_axis(S, NB, axis=1)
    iu = np.triu_indices(n, 1); sims = S[iu]
    o = np.argsort(sims)[::-1]; ei, ej, es = iu[0][o], iu[1][o], sims[o]
    parent = np.arange(n); size = np.ones(n, int)
    members = {i: [i] for i in range(n)}
    wsum = 0.0; wcnt = 0
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    C = np.full(len(taus), np.nan); Snn = np.full(len(taus), np.nan)
    e = 0; E = len(es)
    for ti, t in enumerate(taus):
        while e < E and es[e] >= t:
            a, b = find(ei[e]), find(ej[e])
            if a != b:
                ma, mb = members[a], members[b]
                blk = S[np.ix_(ma, mb)]
                wsum += float(blk.sum()); wcnt += len(ma) * len(mb)
                if size[a] < size[b]: a, b = b, a; ma, mb = mb, ma
                parent[b] = a; size[a] += size[b]; members[a] = ma + mb; del members[b]
            e += 1
        C[ti] = wsum / wcnt if wcnt else np.nan
        if ti in ckset:
            lab = np.empty(n, int)
            for r, ms in members.items(): lab[ms] = r
            ext = lab[NB] != lab[:, None]
            has = ext.any(1)
            first = np.argmax(ext, axis=1)
            cardbest = np.where(has, NBs[np.arange(n), first], -1.0)
            best = collections.defaultdict(lambda: -1.0)
            for i in range(n):
                r = lab[i]
                if cardbest[i] > best[r]: best[r] = cardbest[i]
            vals = [v for v in best.values() if v > 0]
            Snn[ti] = np.mean(vals) if vals else np.nan
    return C, Snn

rng = np.random.default_rng(seed_base)
seeds = [rng.integers(1e9) for _ in range(500)]
Cs = []; Ss = []; ns = []
for r in range(nrep):
    m = int(round(frac * N))
    if m >= N:
        idx = np.arange(N)
    else:
        rr = np.random.default_rng(seeds[r])
        idx = np.sort(rr.choice(N, m, replace=False))
    C, Snn = sweep(idx)
    Cs.append(C); Ss.append(Snn); ns.append(len(idx))
    print('frac', frac, 'rep', r, 'n', len(idx), 'done', flush=True)
np.savez(f'data/experiments/review/cohdiv_frac_{suf}.npz',
         taus=taus, C=np.array(Cs), S=np.array(Ss), ns=np.array(ns), frac=frac)
print('saved', suf)
