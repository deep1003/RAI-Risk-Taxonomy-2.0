# build_flow_review_v2.py — regenerate f1.html / f4.html human-audit pages
# Same visual format as c70.html (build_review_pages.build_set) + 3-criterion human-audit column (EM re-assignment basis)
import json, os, html as H
from collections import defaultdict

OUT='data/experiments/review'

HI=json.load(open('public/data/releases/v2.18.0-rc/hierarchy.json'))
nd={n['node_id']:n for n in HI['nodes']}

L1_ORDER=['RAI1-G','RAI1-A','RAI1-P']
SUF_ORDER={'SYS':0,'INT':1,'SOC':2,'HLD':3}

MASTER={c['l4_id']:c for c in json.load(open('data/experiments/stage1/out/master.json'))['cards']}

# Societal Safety scope split: the SOC axis is one concept family applied at three scopes.
# L3 numbering is shared across scopes (RAI3-{G|A|P}-SOC-nn denotes the same risk concept);
# L4 identifiers are unchanged, only the owning L3 branches by scope.
SOC_SCOPE={}
with open(f'{OUT}/master_soc_scope_mapping.csv', encoding='utf-8') as fh:
    next(fh)
    for line in fh:
        parts=line.rstrip('\n').split(',')
        if len(parts)>=5: SOC_SCOPE[parts[0]]=(parts[3], parts[4])
for scope in ('A','P'):
    g2, n2 = 'RAI2-G-SOC', f'RAI2-{scope}-SOC'
    src=nd[g2]
    nd[n2]=dict(src, node_id=n2, parent_id=f'RAI1-{scope}')
    for k in range(1,12):
        g3=f'RAI3-G-SOC-{k:02d}'
        if g3 not in nd: continue
        n3=f'RAI3-{scope}-SOC-{k:02d}'
        nd[n3]=dict(nd[g3], node_id=n3, parent_id=n2)

def apply_soc_scope(cards):
    """Route SOC cards to the General, Agentic or Physical scope of the same L3 concept."""
    for c in cards:
        m=SOC_SCOPE.get(c['rep'])
        if m and '-SOC-' in c['l3'] and m[0] in nd:
            c['l3']=m[0]
    return cards

def esc(s): return H.escape(s or '')

CSS = """
details.crit{border:1px solid #d8d2c2;background:#fbf9f3;border-radius:6px;margin:10px 0;padding:6px 12px}
details.crit summary{cursor:pointer;font-size:13px}
.critb p{font-size:12px;line-height:1.7;color:#3a3a3a;margin:6px 0}

*{box-sizing:border-box}
body{font-family:'Apple SD Gothic Neo','Noto Sans KR',-apple-system,sans-serif;margin:0;color:#1c1c1c;background:#fff}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 18px;z-index:20}
h1{font-size:18px;margin:0 0 6px} .sub{color:#555;font-size:12.5px;line-height:1.7}
nav a{display:inline-block;margin-right:10px;padding:4px 11px;border:1px solid #bbb;border-radius:14px;
 text-decoration:none;color:#333;font-size:12.5px}
nav a.on{background:#2a2a2a;color:#fff;border-color:#2a2a2a}
.tools{margin-top:8px;display:flex;gap:7px;flex-wrap:wrap;align-items:center}
input[type=text]{padding:5px 9px;font-size:13px;border:1px solid #ccc;border-radius:4px;width:300px}
button{padding:4px 10px;border:1px solid #bbb;border-radius:4px;background:#fff;cursor:pointer;font-size:12.5px}
button.save{background:#0f6e56;color:#fff;border-color:#0f6e56}
button.on{background:#2a2a2a;color:#fff}
main{padding:14px 18px 90px}
.l1{margin-top:22px;border-top:3px solid #2a2a2a;padding-top:10px}
.l1 h2{font-size:17px;margin:0 0 2px} .l1 .n{color:#888;font-size:12px;font-weight:400}
.l2{margin:14px 0 0 6px;border-left:3px solid #c9d3cf;padding-left:12px}
.l2 h3{font-size:15px;margin:0 0 4px;color:#2c4a41}
details.l3{margin:6px 0;border:1px solid #e2e2e2;border-radius:6px;background:#fcfcfc}
details.l3>summary{cursor:pointer;padding:7px 10px;font-size:13.5px;list-style:none}
details.l3>summary::-webkit-details-marker{display:none}
details.l3>summary::before{content:'▸ ';color:#888}
details.l3[open]>summary::before{content:'▾ '}
details.l3>summary .cnt{color:#0f6e56;font-weight:600;margin-left:6px}
details.l3>summary .en{color:#777;font-weight:400;font-size:11.5px}
details.l3>summary .l3hr{float:right;min-width:180px;border:1px solid #d5d5d5;border-radius:4px;
  background:#fff;padding:2px 7px;font-size:12px;font-weight:400;color:#333;margin-left:10px}
details.l3>summary .l3hr:empty::before{content:'Human audit';color:#bbb}
details.l3>summary .l3hr:focus{outline:none;border-color:#2a5a8a;background:#f7fbff}
.l3def{padding:0 12px 6px;color:#666;font-size:11.5px;border-bottom:1px dotted #e5e5e5;margin-bottom:4px}
table.cards{width:100%;border-collapse:collapse;font-size:12.5px}
table.cards th{background:#f5f5f3;font-weight:600;padding:5px 8px;border:1px solid #e6e6e6;text-align:left;font-size:11.5px}
table.cards td{border:1px solid #ececec;padding:6px 8px;vertical-align:top}
.id{font-family:ui-monospace,monospace;font-size:11px;color:#888;white-space:nowrap;width:96px}
.lab{font-weight:600} .en{color:#3c3489;font-size:11.5px}
.def{color:#3a3a3a;font-size:11.5px;margin-top:3px} .defe{color:#777;font-size:11px;margin-top:2px}
.meta{color:#999;font-size:10.5px;margin-top:4px}
.tag{display:inline-block;border-radius:3px;padding:0 5px;font-size:10px;margin-right:3px}
.t-mrg{background:#e1f5ee;color:#0f6e56} .t-ref{background:#eeedfe;color:#3c3489}
.t-cfl{background:#fdecec;color:#a32d2d}
.t-hold{background:#fdf3d7;color:#8a6410;border:1px solid #e8cf8a}

details.mem{margin-top:5px;font-size:11px;color:#666}
details.mem>summary{cursor:pointer;font-size:10.5px;color:#8a8a8a}
details.mem .memb{margin-top:3px;padding:4px 8px;background:#f7f6f1;border-radius:4px;font-size:10.5px;color:#555}
details.mem .mid{font-family:ui-monospace,monospace;font-size:10px;color:#888;margin-right:4px}
details.mem .memb div{margin:1px 0}
.hv{width:190px}
.judge{font-size:11px;line-height:1.5}
.judge .jrow{margin:2px 0;white-space:nowrap}
.judge .jt{font-weight:600;color:#444;margin-right:4px}
.judge label{margin-right:6px;cursor:pointer;color:#333}
.judge input[type=radio]{vertical-align:-1px;margin:0 2px 0 0}
.judge input.memo{width:140px;padding:2px 5px;font-size:11px;border:1px solid #ccc;border-radius:3px;margin-top:3px}


.hidden{display:none!important}
table.summary{border-collapse:collapse;font-size:12px;margin:8px 0 2px}
table.summary th,table.summary td{border:1px solid #e2e2e2;padding:4px 9px;text-align:left;white-space:nowrap}
table.summary th{background:#f5f5f3;font-weight:600}
table.summary td.n{text-align:right;font-variant-numeric:tabular-nums}
table.summary tr.cur td{background:#eef4f9;font-weight:600}
table.summary td.hr{min-width:150px;background:#fff;font-weight:400}
table.summary td.hr:focus{outline:1px solid #2a5a8a}
label.imp{padding:4px 10px;border:1px solid #bbb;border-radius:4px;background:#fff;cursor:pointer;font-size:12.5px}
label.imp:hover{border-color:#2a5a8a}
button.reset{color:#a33}
.savemsg{color:#8a8a8a;font-size:12px}
details.ov{margin:8px 0 2px}details.ov>summary{cursor:pointer;font-size:12.5px;color:#2a5a8a}
main{padding-bottom:74px}
#bbar{position:fixed;left:0;right:0;bottom:0;background:#2a2a2a;color:#eee;font-size:12.5px;
 box-shadow:0 -2px 10px rgba(0,0,0,.18);
 padding:8px 18px;display:flex;gap:14px;align-items:center;z-index:30}
#bbar button{background:#0f6e56;color:#fff;border:none;padding:5px 12px;border-radius:4px}
#pbar{flex:0 0 220px;height:8px;background:#555;border-radius:4px;overflow:hidden}
#pfill{height:100%;width:0;background:#7dd3b0}
"""

JS_TMPL = """
const TIER='__TIER__';
const rows=[...document.querySelectorAll('tr.card')];
const dets=[...document.querySelectorAll('details.l3')];
let filt='';
function apply(){
  const q=document.getElementById('q').value.toLowerCase();
  let shown=0;
  rows.forEach(r=>{
    let ok=(!q||r.dataset.s.includes(q));
    if(filt==='merged') ok=ok&&r.dataset.m==='1';
    if(filt==='hold') ok=ok&&r.dataset.h==='1';
    r.classList.toggle('hidden',!ok); if(ok)shown++;
  });
  dets.forEach(d=>{
    const n=[...d.querySelectorAll('tr.card')].filter(r=>!r.classList.contains('hidden')).length;
    d.classList.toggle('hidden',n===0);
    if((q||filt)&&n) d.open=true;
    const c=d.querySelector('.shown'); if(c) c.textContent=(q||filt)?(' / '+n+' shown'):'';
  });
  document.querySelectorAll('.l2,.l1').forEach(g=>{
    const n=[...g.querySelectorAll('details.l3')].filter(d=>!d.classList.contains('hidden')).length;
    g.classList.toggle('hidden',n===0);
  });
  document.getElementById('cnt').textContent=shown+' cards shown';
  prog();
}
function answered(r){
  const id=r.dataset.id;
  return ['d_','m_','r_'].every(p=>document.querySelector('input[name="'+p+id+'"]:checked'));
}
function prog(){
  const vis=rows.filter(r=>!r.classList.contains('hidden'));
  const done=vis.filter(answered).length;
  document.getElementById('ptxt').textContent='Audit progress '+done+' / '+vis.length;
  document.getElementById('pfill').style.width=(vis.length?100*done/vis.length:0)+'%';
}
function val(name){const e=document.querySelector('input[name="'+name+'"]:checked');return e?e.value:null;}

/* ---- persistence: the browser keeps the work, the JSON file carries it out ---- */
const KEY='rai_audit_'+TIER;
const notes=()=>[...document.querySelectorAll('[data-note]')];
function collect(){
  const audit=rows.map(r=>{const id=r.dataset.id;
    return {rep:id, desc_ok:val('d_'+id), l3_ok:val('m_'+id), dup:val('r_'+id),
      memo:(r.querySelector('input.memo')||{}).value||''};})
    .filter(x=>x.desc_ok||x.l3_ok||x.dup||x.memo);
  const note={};
  notes().forEach(n=>{const t=n.textContent.trim(); if(t) note[n.dataset.note]=t;});
  return {tier:TIER, saved_at:new Date().toISOString(), audit:audit, notes:note};
}
function stamp(m){const e=document.getElementById('save');if(e)e.textContent=m;}
let timer=null;
function save(){
  clearTimeout(timer);
  timer=setTimeout(()=>{
    try{
      const d=collect();
      localStorage.setItem(KEY,JSON.stringify(d));
      stamp('Saved '+new Date().toLocaleTimeString()+' \u00b7 '+d.audit.length+' cards judged');
    }catch(err){stamp('Autosave unavailable here \u2014 export before closing');}
  },400);
}
function restore(d){
  if(!d||!d.audit) return 0;
  let n=0;
  d.audit.forEach(x=>{
    [['d_','desc_ok'],['m_','l3_ok'],['r_','dup']].forEach(function(pair){
      if(!x[pair[1]]) return;
      const el=document.querySelector('input[name="'+pair[0]+x.rep+'"][value="'+x[pair[1]]+'"]');
      if(el) el.checked=true;
    });
    const row=document.querySelector('tr.card[data-id="'+x.rep+'"]');
    if(row&&x.memo){const m=row.querySelector('input.memo'); if(m) m.value=x.memo;}
    n++;
  });
  if(d.notes) notes().forEach(el=>{const v=d.notes[el.dataset.note]; if(v) el.textContent=v;});
  return n;
}
try{
  const raw=localStorage.getItem(KEY);
  if(raw){
    const d=JSON.parse(raw);
    const n=restore(d);
    stamp('Restored '+n+' judgments from '+new Date(d.saved_at).toLocaleString());
  } else stamp('Autosave on \u2014 this browser keeps your work');
}catch(err){stamp('Autosave unavailable here \u2014 export before closing');}

document.addEventListener('input',e=>{if(e.target.matches('input'))save();});
document.addEventListener('change',e=>{if(e.target.matches('input'))save();});
document.addEventListener('blur',e=>{if(e.target.matches&&e.target.matches('[data-note]'))save();},true);

function exportJSON(){
  const blob=new Blob([JSON.stringify(collect(),null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=TIER+'_audit_'+new Date().toISOString().slice(0,10)+'.json';a.click();
  stamp('Exported '+new Date().toLocaleTimeString());
}
document.getElementById('exp').addEventListener('click',exportJSON);
document.getElementById('exp2').addEventListener('click',exportJSON);
document.getElementById('impf').addEventListener('change',e=>{
  const f=e.target.files[0]; if(!f) return;
  const rd=new FileReader();
  rd.onload=()=>{try{const n=restore(JSON.parse(rd.result));save();prog();
    stamp('Imported '+n+' judgments');}catch(err){stamp('Could not read that file');}};
  rd.readAsText(f);
});
document.getElementById('reset').addEventListener('click',()=>{
  if(!confirm('Discard every judgment saved in this browser for '+TIER.toUpperCase()+'?')) return;
  localStorage.removeItem(KEY); location.reload();
});
document.addEventListener('change',e=>{if(e.target.matches('.judge input[type=radio]'))prog();});
document.getElementById('q').addEventListener('input',apply);
document.querySelectorAll('.tools button[data-f]').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.tools button[data-f]').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); filt=b.dataset.f; apply();}));
document.getElementById('expand').addEventListener('click',()=>dets.forEach(d=>d.open=true));
document.getElementById('collapse').addEventListener('click',()=>dets.forEach(d=>d.open=false));
apply();
"""

def judge_cell(rep):
    def pair(prefix, num, txt):
        nm=f"{prefix}_{rep}"
        return (f"<div class=jrow><span class=jt>{num} {txt}</span>"
                f"<label><input type=radio name='{nm}' value=yes>Yes</label>"
                f"<label><input type=radio name='{nm}' value=no>No</label></div>")
    return ("<td class=hv><div class=judge>"
            + pair('d','①','Description')
            + pair('m','②','L3 mapping')
            + pair('r','③','Duplicate')
            + "<input class=memo type=text placeholder='notes'>"
            + "</div></td>")

TIERS=[
 ('Master','–','1,612','–','–','1,154 / 155 / 303','canonical inventory'),
 ('F1','0.8329','1,383','109','229','906 / 140 / 337','fidelity tier (crossing)'),
 ('F2','0.8033','1,154','121','458','734 / 128 / 292','second consolidation'),
 ('F3','0.7903','1,038','81','574','653 / 112 / 273','third consolidation'),
 ('F4','0.7753','901','82','711','568 / 92 / 241','compression tier'),
 ('F5','0.7634','792','70','820','491 / 83 / 218','extended compression tier'),
]

def tier_summary(cur):
    rows=[]
    for name,tau,n,grp,absorbed,gap,role in TIERS:
        cls=" class=cur" if name.lower()==cur else ""
        rows.append(f"<tr{cls}><td>{name}</td><td class=n>{tau}</td><td class=n>{n}</td>"
                    f"<td class=n>{grp}</td><td class=n>{absorbed}</td><td class=n>{gap}</td><td>{role}</td>"
                    f"<td class=hr contenteditable=true data-note='tier:{name}'></td></tr>")
    return ("<details class=ov><summary>Tier overview (granularity flow)</summary>"
            "<table class=summary><tr><th>Tier</th><th>\u03c4*</th><th>Cards</th><th>Merge groups</th>"
            "<th>Absorbed</th><th>G / A / P</th><th>Role</th><th>Human audit</th></tr>"+''.join(rows)+"</table>"
            "<div style='font-size:11.5px;color:#777;margin-top:4px'>Merge groups and absorbed cards are, respectively, per consolidation step and cumulative from the Master inventory. The F4 page reports 211 refined groups, the cumulative count over steps 1\u20134. The Societal Safety axis is one concept family applied at three scopes, so its cards are counted under General, Agentic or Physical (RAI3-{G|A|P}-SOC-nn share the same numbering and meaning).</div></details>")

def build(page_id, cards, title, sub_extra):
    cards=apply_soc_scope(cards)
    byl3=defaultdict(list)
    for c in cards: byl3[c['l3']].append(c)
    # Hierarchy layout: L1 -> L2 -> L3
    l3_by_l2=defaultdict(list)
    l2_by_l1=defaultdict(set)
    for l3id in byl3:
        l2=nd[l3id]['parent_id']
        l3_by_l2[l2].append(l3id)
        l2_by_l1[nd[l2]['parent_id']].add(l2)
    for k in l3_by_l2: l3_by_l2[k].sort()
    total=len(cards)
    body=''
    for l1 in L1_ORDER:
        l2s=sorted(l2_by_l1.get(l1,[]), key=lambda x:(SUF_ORDER.get(x.split('-')[-1],9),x))
        if not l2s: continue
        l1n=nd[l1]; sec=''; l1cnt=0
        for l2 in l2s:
            l2n=nd[l2]; blocks=''; l2cnt=0
            for l3id in l3_by_l2[l2]:
                n=nd[l3id]
                items=sorted(byl3[l3id], key=lambda y:y['rep'])
                l2cnt+=len(items)
                trs=''
                for x in items:
                    i=x['rep']; merged=x['n']>1; refined=bool(x.get('refined'))
                    hold=x.get('em_status')=='hold'
                    sstr=(i+' '+(x.get('label_ko') or '')+' '+(x.get('label_en') or '')+' '
                          +(x.get('definition_ko') or '')+' '+(x.get('definition_en') or '')).lower()
                    if merged: sstr+=' '+' '.join(x['members']).lower()
                    badges=''
                    holdb=''
                    memblock=''
                    if merged:
                        lis=''.join(f"<div><span class=mid>{m}</span>{esc((MASTER.get(m) or {}).get('label_ko'))}</div>"
                                    for m in x['members'])
                        memblock=(f"<details class=mem><summary>Source members ({x['n']})</summary>"
                                  f"<div class=memb><b>Source:</b> min_cos={x['min_cos']:.4f}"
                                  + (" · <b style='color:#a32d2d'>Mixed L3</b>" if x.get('l3_conflict') else '')
                                  + lis + "</div></details>")
                    cls='card'+(' mrg' if merged else '')+(' hold' if hold else '')
                    trs+=(f"<tr class='{cls}' data-id='{i}' data-l3='{l3id}' "
                          f"data-m='{1 if merged else 0}' data-h='{1 if hold else 0}' data-s=\"{esc(sstr)}\">"
                          f"<td class=id>{i}{holdb}</td>"
                          f"<td><div class=lab>{esc(x.get('label_ko'))}</div>"
                          f"<div class=en>{esc(x.get('label_en'))}</div>"
                          f"<div class=def>{esc(x.get('definition_ko'))}</div>"
                          f"<div class=defe>{esc(x.get('definition_en'))}</div>"
                          + ""
                          + memblock + "</td>"
                          + judge_cell(i) + "</tr>")
                blocks+=(f"<details class=l3><summary><code>{l3id}</code> {esc(n['label_ko'])} "
                         f"<span class=en>{esc(n.get('label_en'))}</span>"
                         f"<span class=cnt>{len(items)} cards</span><span class=shown></span>"
                         f"<span class=l3hr contenteditable=true data-note='l3:{l3id}' "
                         f"onclick=\"event.preventDefault();event.stopPropagation()\"></span></summary>"
                         f"<div class=l3def>{esc(n.get('definition_ko') or n.get('definition_en'))}</div>"
                         f"<table class=cards><tr><th>ID</th><th>Card</th>"
                         f"<th>Human audit</th></tr>{trs}</table></details>")
            if blocks:
                l1cnt+=l2cnt
                sec+=(f"<div class=l2><h3>{esc(l2n['label_ko'])} <span class=n>· {esc(l2n.get('label_en'))} "
                      f"· {l2cnt} cards</span></h3>{blocks}</div>")
        if sec:
            body+=(f"<div class=l1><h2>{esc(l1n['label_ko'])} <span class=n>· {esc(l1n.get('label_en'))} "
                   f"· {l1cnt} cards</span></h2>{sec}</div>")
    nav=(f"<nav><a href='index.html'>Overview</a>"
         f"<a href='f1.html' class='{'on' if page_id=='f1' else ''}'>F1 audit</a>"
         f"<a href='f4.html' class='{'on' if page_id=='f4' else ''}'>F4 audit</a>"
         f"<a href='f5.html' class='{'on' if page_id=='f5' else ''}'>F5 audit</a>"
         f"<a href='glossary.html'>Glossary</a>"
         f"</nav>")
    summary=tier_summary(page_id)
    nmerged=sum(1 for c in cards if c['n']>1)
    nhold=sum(1 for c in cards if c.get('em_status')=='hold')
    js=JS_TMPL.replace('__TIER__', page_id)
    page=(f"<!doctype html><html lang=en><head><meta charset=utf-8><title>{title}</title><style>{CSS}</style></head><body>"
          f"<header><h1>{title}</h1>"
          f"<div class=sub>Total <b>{total} cards</b> · {len(byl3)} L3 categories in use · {nmerged} merged groups · {sub_extra} "
          f"Hierarchy order: General → Agentic → Physical. "
          f"Review criteria: <b>① Description adequacy</b> (is the risk correctly described?) · <b>② L3 mapping</b> (is the assigned L3 appropriate?) · "
          f"<b>③ Redundancy</b> (does it duplicate other cards?). "
          f"L3 assignments are re-derived by the seed-anchored hybrid EM.</div>{summary}{nav}"
          f"<div class=tools><input type=text id=q placeholder='Search: ID / label / definition (KO·EN)'>"
          f"<button data-f='' class=on>All</button>"
          f"<button data-f=merged>Merged only</button>"
          ""
          f"<button id=expand>Expand all</button><button id=collapse>Collapse all</button>"
          f"<button id=exp2 class=save>Save / export JSON</button>"
          f"<span id=cnt class=sub></span></div></header><main>{body}</main>"
          f"<div id=bbar><span id=ptxt>Audit progress 0 / {total}</span><div id=pbar><div id=pfill></div></div>"
          f"<button id=exp>Export judgments (JSON)</button>"
          f"<label class=imp for=impf>Import JSON</label>"
          f"<input id=impf type=file accept='.json' hidden>"
          f"<button id=reset class=reset>Clear</button>"
          f"<span id=save class=savemsg></span></div>"
          f"<script>{js}</script></body></html>")
    open(f'{OUT}/{page_id}.html','w').write(page)
    print(page_id, total, 'cards,', nmerged, 'merged,', nhold, 'hold,', len(byl3), 'L3')

F1=json.load(open(f'{OUT}/f1_state.json'))
build('f1', F1['cards'],
      'F1 — granularity-flow tier 1 (human audit)',
      f"τ={F1['tau']:.4f} · representative text is the medoid original · L3 re-assigned by EM.")

F4=json.load(open(f'{OUT}/flow4_cards_full.json'))
build('f4', F4['cards'],
      'F4 — granularity-flow tier 4 (human audit)',
      'τ* 0.8329→0.7753 · L3 re-assigned by EM.')

F5=json.load(open(f'{OUT}/f5_state.json'))
build('f5', F5['cards'],
      'F5 — granularity-flow tier 5 (human audit)',
      'τ* 0.8329→0.7634 · L3 propagated from the F4 EM assignment.')
