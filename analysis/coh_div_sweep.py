# 응집(C) vs 군집간 최강 외부유사도(S_nn) 스윕 — 벡터화판
import numpy as np, sys
start,nrep,suf=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
emb=np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X=emb/np.linalg.norm(emb,axis=1,keepdims=True)
Sfull=(X@X.T).astype(np.float32); N=Sfull.shape[0]
taus=np.round(np.arange(0.9400,0.49999,-0.0001),4)
ckset=set(range(0,len(taus),20))  # 0.002 간격 체크포인트
K=96
def sweep(idx):
    S=Sfull[np.ix_(idx,idx)]; n=len(idx)
    part=np.argpartition(-S,K+1,axis=1)[:,:K+1]
    rowv=np.take_along_axis(S,part,axis=1)
    ordr=np.argsort(-rowv,axis=1)
    NB=np.take_along_axis(part,ordr,axis=1)
    NB=np.where(NB==np.arange(n)[:,None], NB, NB)  # self 포함 가능; 아래서 라벨 비교로 처리
    NBs=np.take_along_axis(S,NB,axis=1)
    iu=np.triu_indices(n,1); sims=S[iu]
    o=np.argsort(sims)[::-1]; ei,ej,es=iu[0][o],iu[1][o],sims[o]
    parent=np.arange(n); size=np.ones(n,int)
    members={i:[i] for i in range(n)}
    wsum=0.0; wcnt=0
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    C=np.full(len(taus),np.nan); Snn=np.full(len(taus),np.nan)
    e=0;E=len(es)
    for ti,t in enumerate(taus):
        while e<E and es[e]>=t:
            a,b=find(ei[e]),find(ej[e])
            if a!=b:
                ma,mb=members[a],members[b]
                blk=S[np.ix_(ma,mb)]
                wsum+=float(blk.sum()); wcnt+=len(ma)*len(mb)
                if size[a]<size[b]: a,b=b,a; ma,mb=mb,ma
                parent[b]=a; size[a]+=size[b]; members[a]=ma+mb; del members[b]
            e+=1
        C[ti]=wsum/wcnt if wcnt else np.nan
        if ti in ckset:
            lab=np.empty(n,int)
            for r,ms in members.items(): lab[ms]=r
            ext=lab[NB]!=lab[:,None]           # (n,K+1) 외부 여부
            has=ext.any(1)
            first=np.argmax(ext,axis=1)
            cardbest=np.where(has,NBs[np.arange(n),first],-1.0)  # 카드별 최강 외부 유사도
            # 군집별 최댓값의 평균
            import collections
            best=collections.defaultdict(lambda:-1.0)
            for i in range(n):
                r=lab[i]
                if cardbest[i]>best[r]: best[r]=cardbest[i]
            vals=[v for v in best.values() if v>0]
            Snn[ti]=np.mean(vals) if vals else np.nan
    return C,Snn
rng=np.random.default_rng(1000)
seeds=[rng.integers(1e9) for _ in range(200)]
Cs=[];Ss=[]
for r in range(start,start+nrep):
    rr=np.random.default_rng(seeds[r])
    idx=np.sort(rr.choice(N,int(0.8*N),replace=False))
    C,Snn=sweep(idx)
    Cs.append(C);Ss.append(Snn)
    print('rep',r,'done',flush=True)
np.savez(f'data/experiments/review/cohdiv_{suf}.npz',taus=taus,C=np.array(Cs),S=np.array(Ss))
print('saved',suf)
