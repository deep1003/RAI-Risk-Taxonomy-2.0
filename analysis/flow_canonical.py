# 정본 granularity flow (재현 가능 사양, 재개 지원)
# 사양: 코사인 그래프, 0.0001 격자, coh=풀링 평균, att=군집별 최대 외부 유사도(전수), 교차=coh<=att 첫 격자점
# 병합: 교차점에서 연결 성분, medoid(현 단계 유사도 평균 최대) 대표. null: 크기별 60추출 z.
import numpy as np, json, os, sys
emb=np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X=emb/np.linalg.norm(emb,axis=1,keepdims=True)
cards=json.load(open('data/experiments/stage1/out/master.json'))['cards']
ids=[c['l4_id'] for c in cards]; N=len(cards)
SF='data/experiments/review/flow_states.json'
st=json.load(open(SF)) if os.path.exists(SF) else dict(steps=[],alive=list(range(N)),members={str(i):[i] for i in range(N)})
alive=st['alive']; members={int(k):v for k,v in st['members'].items()}
rng=np.random.default_rng(4)
def one_step(alive,members):
    A=X[alive]; n=len(alive); S=(A@A.T).astype(np.float32); np.fill_diagonal(S,-1)
    iu=np.triu_indices(n,1); sims=S[iu]
    o=np.argsort(sims)[::-1]; ei,ej,es=iu[0][o],iu[1][o],sims[o]
    taus=np.round(np.arange(round(float(es[0]),4),0.60,-0.0001),4)
    parent=np.arange(n); mem={i:[i] for i in range(n)}; size=np.ones(n,int)
    wsum=0.0; wcnt=0
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    e=0;E=len(es); tstar=None
    for t in taus:
        merged=False
        while e<E and es[e]>=t:
            a,b=find(ei[e]),find(ej[e])
            if a!=b:
                ma,mb=mem[a],mem[b]; blk=S[np.ix_(ma,mb)]
                wsum+=float(blk.sum()); wcnt+=len(ma)*len(mb)
                if size[a]<size[b]: a,b=b,a; ma,mb=mb,ma
                parent[b]=a; size[a]+=size[b]; mem[a]=ma+mb; del mem[b]
                merged=True
            e+=1
        if wcnt==0: continue
        if not merged and tstar is None and t!=taus[0]: pass
        coh=wsum/wcnt
        roots=np.array([find(i) for i in range(n)])
        # att 전수: 각 군집 r의 최대 외부 유사도 = max over i in r of max_j∉r S[i,j]
        att_vals=[]
        # 효율: S의 행 최대를 군집 제외로 — 군집별로 마스크
        for r,mm in mem.items():
            sub=S[mm][:,:]
            mask=np.ones(n,bool); mask[mm]=False
            if mask.any():
                att_vals.append(float(sub[:,mask].max()))
        if len(att_vals)<2: return None,None,None,None
        att=float(np.mean(att_vals))
        if coh<=att:
            tstar=float(t); break
    if tstar is None: return None,None,None,None
    # 확정 병합
    parent=np.arange(n)
    def find2(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    ii,jj=np.where(np.triu(S,1)>=tstar)
    for a,b in zip(ii,jj):
        ra,rb=find2(a),find2(b)
        if ra!=rb: parent[rb]=ra
    lab=np.array([find2(i) for i in range(n)])
    new_alive=[];new_members={};gstats=[]
    for r in set(lab.tolist()):
        mloc=np.where(lab==r)[0]; orig=[alive[i] for i in mloc]
        allmem=[m for i in orig for m in members[i]]
        if len(mloc)==1: keep=orig[0]
        else:
            sub=S[np.ix_(mloc,mloc)]; keep=orig[int(np.argmax(sub.mean(1)))]
            gstats.append((len(mloc),float(sub[np.triu_indices(len(mloc),1)].min())))
        new_alive.append(keep); new_members[keep]=allmem
    # null z (현 단계 S 기준, 크기별 60추출)
    zs=[]
    if gstats:
        nulls={}
        for k in set(g[0] for g in gstats):
            vals=[]
            for _ in range(60):
                idx=rng.choice(n,k,replace=False)
                sub=S[np.ix_(idx,idx)]; vals.append(sub[np.triu_indices(k,1)].min())
            nulls[k]=(float(np.mean(vals)),float(np.std(vals)))
        for k,mn in gstats:
            mu,sd=nulls[k]; zs.append((mn-mu)/sd if sd>0 else np.inf)
    info=dict(tau=tstar,n_before=n,n_after=len(new_alive),groups=len(gstats),
              med_min=float(np.median([g[1] for g in gstats])) if gstats else None,
              med_z=float(np.median(zs)) if zs else None,
              frac2=float(np.mean([z>2 for z in zs])) if zs else None)
    return tstar,new_alive,new_members,info
done=len(st['steps']); budget=int(sys.argv[1]) if len(sys.argv)>1 else 2
for _ in range(budget):
    tstar,na,nm,info=one_step(alive,members)
    if tstar is None:
        st['finished']=True; print('flow finished at',len(st['steps']),'steps'); break
    alive,members=na,nm
    st['steps'].append(info)
    st['alive']=alive; st['members']={str(k):v for k,v in members.items()}
    json.dump(st,open(SF,'w'))
    print('step %d: tau*=%.4f n %d->%d groups=%d med_z=%.2f frac2=%.2f'%(
        len(st['steps']),info['tau'],info['n_before'],info['n_after'],info['groups'],info['med_z'],info['frac2']),flush=True)
    if len(st['steps'])==4:
        out=[]
        for k in alive:
            mem=members[k]
            if len(mem)>1:
                sub=X[mem]@X[mem].T; mn=float(sub[np.triu_indices(len(mem),1)].min())
            else: mn=None
            out.append(dict(rep=ids[k],members=[ids[m] for m in mem],n=len(mem),min_cos=mn))
        json.dump(dict(taus=[s['tau'] for s in st['steps']],cards=out),
                  open('data/experiments/review/flow4_state.json','w'),ensure_ascii=False,indent=1)
        print('flow4_state.json saved (%d cards)'%len(out),flush=True)
