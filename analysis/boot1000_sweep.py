# Figure 1용 1000회 부분표본 스윕 (경량: 이벤트 기반, 기록격자 0.0005)
# usage: python3 boot1000_sweep.py <start> <n> <suffix>
import numpy as np, sys
start,nrep,suf=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
emb=np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X=emb/np.linalg.norm(emb,axis=1,keepdims=True)
Sfull=(X@X.T).astype(np.float32); N=Sfull.shape[0]
taus=np.round(np.arange(0.9400,0.49999,-0.0005),4)
T=len(taus)
def sweep(S):
    n=S.shape[0]
    iu=np.triu_indices(n,1); sims=S[iu]
    o=np.argsort(sims)[::-1]; ei,ej,es=iu[0][o],iu[1][o],sims[o]
    parent=np.arange(n); size=np.ones(n,int)
    members={i:[i] for i in range(n)}
    cmin={}; wsum=0.0; wcnt=0; msum=0.0; mcnt=0; ncl=n
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    out=np.empty((T,5),np.float32); e=0;E=len(es)
    top2=[1,0]
    for ti,t in enumerate(taus):
        while e<E and es[e]>=t:
            a,b=find(ei[e]),find(ej[e])
            if a!=b:
                ma,mb=members[a],members[b]
                blk=S[np.ix_(ma,mb)]
                wsum+=float(blk.sum()); wcnt+=len(ma)*len(mb)
                bm=float(blk.min()); oa=cmin.get(a); ob=cmin.get(b)
                nm=bm
                if oa is not None: nm=min(nm,oa); msum-=oa; mcnt-=1
                if ob is not None: nm=min(nm,ob); msum-=ob; mcnt-=1
                if size[a]<size[b]: a,b=b,a; ma,mb=mb,ma
                parent[b]=a; size[a]+=size[b]; members[a]=ma+mb; del members[b]
                cmin.pop(b,None); cmin[a]=nm; msum+=nm; mcnt+=1
                ncl-=1
            e+=1
        if ti%4==0 or ti==T-1:   # 크기 정렬은 드물게
            ss=sorted((size[r] for r in members),reverse=True)
            top2=[ss[0],ss[1] if len(ss)>1 else 0]
        out[ti]=[wsum/wcnt if wcnt else np.nan, msum/mcnt if mcnt else np.nan, ncl, top2[0], top2[1]]
    return out
rng=np.random.default_rng(2000)
seeds=[int(rng.integers(1e9)) for _ in range(2000)]
acc_sum=np.zeros((T,5)); acc_sq=np.zeros((T,5)); cnt=0
t1s=[];t2s=[]; w=20  # 0.01 창
for r in range(start,start+nrep):
    rr=np.random.default_rng(seeds[r])
    idx=np.sort(rr.choice(N,int(0.8*N),replace=False))
    o=sweep(Sfull[np.ix_(idx,idx)])
    acc_sum+=np.nan_to_num(o); acc_sq+=np.nan_to_num(o)**2; cnt+=1
    mc,mn=o[:,0],o[:,1]
    d1=np.abs(mc[:-w]-mc[w:]); t1s.append(taus[w:][np.nanargmax(d1)]+0.005)
    d2=np.abs(mn[:-w]-mn[w:]); t2s.append(taus[w:][np.nanargmax(d2)]+0.005)
    if r%50==0: print('rep',r,flush=True)
np.savez(f'data/experiments/review/boot1000_{suf}.npz',taus=taus,sum=acc_sum,sq=acc_sq,cnt=cnt,
         t1s=np.array(t1s),t2s=np.array(t2s))
print('saved',suf,cnt)
