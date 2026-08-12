import json, numpy as np, os, sys
BASE='data/experiments/mit_replication'
items=json.load(open(f'{BASE}/mit_risks.json'))
X0=np.load(f'{BASE}/emb_mit_bge.npy')
keep=[i for i,it in enumerate(items) if not ((it['subcategory'] or it['category']).strip() in ('-','–','') and not it['description'].strip())]
X0=X0[keep]
SF=f'{BASE}/mit_flow_states.json'
st=json.load(open(SF)) if os.path.exists(SF) else dict(steps=[],alive=list(range(len(X0))),members={str(i):[i] for i in range(len(X0))})
alive=st['alive']; members={int(k):v for k,v in st['members'].items()}
rng=np.random.default_rng(4)
def one_step(alive,members):
    A=X0[alive]; n=len(alive); S=(A@A.T).astype(np.float32); np.fill_diagonal(S,-1)
    iu=np.triu_indices(n,1); sims=S[iu]
    o=np.argsort(sims)[::-1]; ei,ej,es=iu[0][o],iu[1][o],sims[o]
    taus=np.round(np.arange(round(float(es[0]),4),0.40,-0.0005),4)
    parent=np.arange(n); mem={i:[i] for i in range(n)}; size=np.ones(n,int)
    wsum=0.0; wcnt=0
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    e=0;E=len(es); tstar=None
    for t in taus:
        while e<E and es[e]>=t:
            a,b=find(ei[e]),find(ej[e])
            if a!=b:
                ma,mb=mem[a],mem[b]; blk=S[np.ix_(ma,mb)]
                wsum+=float(blk.sum()); wcnt+=len(ma)*len(mb)
                if size[a]<size[b]: a,b=b,a; ma,mb=mb,ma
                parent[b]=a; size[a]+=size[b]; mem[a]=ma+mb; del mem[b]
            e+=1
        if wcnt==0: continue
        coh=wsum/wcnt
        att=[]
        for r,mm in mem.items():
            mask=np.ones(n,bool); mask[mm]=False
            if mask.any(): att.append(float(S[mm][:,mask].max()))
        if len(att)<2: return None,None,None,None
        if coh<=float(np.mean(att)): tstar=float(t); break
    if tstar is None: return None,None,None,None
    parent=np.arange(n)
    def find2(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    ii,jj=np.where(np.triu(S,1)>=tstar)
    for a,b in zip(ii,jj):
        ra,rb=find2(a),find2(b)
        if ra!=rb: parent[rb]=ra
    lab=np.array([find2(i) for i in range(n)])
    new_alive=[];new_members={};gst=[]
    for r in set(lab.tolist()):
        m=np.where(lab==r)[0]; orig=[alive[i] for i in m]
        allm=[x for i in orig for x in members[i]]
        if len(m)==1: keep_i=orig[0]
        else:
            sub=S[np.ix_(m,m)]; keep_i=orig[int(np.argmax(sub.mean(1)))]
            gst.append((len(m),float(sub[np.triu_indices(len(m),1)].min())))
        new_alive.append(keep_i); new_members[keep_i]=allm
    zs=[]
    if gst:
        nulls={}
        for kk in set(g[0] for g in gst):
            vals=[]
            for _ in range(60):
                idx=rng.choice(n,kk,replace=False)
                sub=S[np.ix_(idx,idx)]; vals.append(sub[np.triu_indices(kk,1)].min())
            nulls[kk]=(float(np.mean(vals)),float(np.std(vals)))
        for kk,mn in gst:
            mu,sd=nulls[kk]; zs.append((mn-mu)/sd if sd>0 else 99)
    info=dict(tau=tstar,n_before=n,n_after=len(new_alive),groups=len(gst),
              med_min=float(np.median([g[1] for g in gst])) if gst else None,
              med_z=float(np.median(zs)) if zs else None,
              frac2=float(np.mean([z>2 for z in zs])) if zs else None)
    return tstar,new_alive,new_members,info
budget=int(sys.argv[1])
for _ in range(budget):
    tstar,na,nm,info=one_step(alive,members)
    if tstar is None: st['finished']=True; print('finished'); break
    alive,members=na,nm
    st['steps'].append(info); st['alive']=alive; st['members']={str(k):v for k,v in members.items()}
    json.dump(st,open(SF,'w'))
    print('step %d: tau*=%.4f n %d->%d groups=%d med_z=%s frac2=%s'%(
        len(st['steps']),info['tau'],info['n_before'],info['n_after'],info['groups'],
        f"{info['med_z']:.2f}" if info['med_z'] else '-',f"{info['frac2']:.2f}" if info['frac2'] else '-'),flush=True)
