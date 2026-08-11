# build_flow_review_v2.py — f1.html / f4.html 휴먼 검수 페이지 재생성
# c70.html(build_review_pages.build_set)과 동일한 시각 포맷 + 3항목 휴먼 검수 열(EM 재배정 기준)
import json, os, html as H
from collections import defaultdict

OUT='data/experiments/review'

HI=json.load(open('public/data/releases/v2.18.0-rc/hierarchy.json'))
nd={n['node_id']:n for n in HI['nodes']}

L1_ORDER=['RAI1-G','RAI1-A','RAI1-P']
SUF_ORDER={'SYS':0,'INT':1,'SOC':2,'HLD':3}

MASTER={c['l4_id']:c for c in json.load(open('data/experiments/stage1/out/master.json'))['cards']}

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
#bbar{position:fixed;left:0;right:0;bottom:0;background:#2a2a2a;color:#eee;font-size:12.5px;
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
    const c=d.querySelector('.shown'); if(c) c.textContent=(q||filt)?(' / '+n+' 표시'):'';
  });
  document.querySelectorAll('.l2,.l1').forEach(g=>{
    const n=[...g.querySelectorAll('details.l3')].filter(d=>!d.classList.contains('hidden')).length;
    g.classList.toggle('hidden',n===0);
  });
  document.getElementById('cnt').textContent=shown+'장 표시';
  prog();
}
function answered(r){
  const id=r.dataset.id;
  return ['d_','m_','r_'].every(p=>document.querySelector('input[name="'+p+id+'"]:checked'));
}
function prog(){
  const vis=rows.filter(r=>!r.classList.contains('hidden'));
  const done=vis.filter(answered).length;
  document.getElementById('ptxt').textContent='진행률 '+done+' / '+vis.length;
  document.getElementById('pfill').style.width=(vis.length?100*done/vis.length:0)+'%';
}
function val(name){const e=document.querySelector('input[name="'+name+'"]:checked');return e?e.value:null;}
document.getElementById('exp').addEventListener('click',()=>{
  const audit=rows.map(r=>{const id=r.dataset.id;
    return {rep:id, desc_ok:val('d_'+id), l3_ok:val('m_'+id), dup:val('r_'+id),
      memo:(r.querySelector('input.memo')||{}).value||''};});
  const blob=new Blob([JSON.stringify({tier:TIER,audit:audit},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=TIER+'_audit.json';a.click();
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
                f"<label><input type=radio name='{nm}' value=yes>예</label>"
                f"<label><input type=radio name='{nm}' value=no>아니오</label></div>")
    return ("<td class=hv><div class=judge>"
            + pair('d','①','기술 적절성')
            + pair('m','②','L3 매핑')
            + pair('r','③','중복성')
            + "<input class=memo type=text placeholder='메모'>"
            + "</div></td>")

def build(page_id, cards, title, sub_extra):
    byl3=defaultdict(list)
    for c in cards: byl3[c['l3']].append(c)
    # 계층 구성: L1 -> L2 -> L3
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
                        memblock=(f"<details class=mem><summary>기존 구성원 {x['n']}장</summary>"
                                  f"<div class=memb><b>기존:</b> min_cos={x['min_cos']:.4f}"
                                  + (" · <b style='color:#a32d2d'>L3 혼재</b>" if x.get('l3_conflict') else '')
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
                         f"<span class=cnt>{len(items)}장</span><span class=shown></span></summary>"
                         f"<div class=l3def>{esc(n.get('definition_ko') or n.get('definition_en'))}</div>"
                         f"<table class=cards><tr><th>ID</th><th>L4 리스크 카드 (한/영 명칭·정의)</th>"
                         f"<th>휴먼 검수 (3기준)</th></tr>{trs}</table></details>")
            if blocks:
                l1cnt+=l2cnt
                sec+=(f"<div class=l2><h3>{esc(l2n['label_ko'])} <span class=n>· {esc(l2n.get('label_en'))} "
                      f"· {l2cnt}장</span></h3>{blocks}</div>")
        if sec:
            body+=(f"<div class=l1><h2>{esc(l1n['label_ko'])} <span class=n>· {esc(l1n.get('label_en'))} "
                   f"· {l1cnt}장</span></h2>{sec}</div>")
    nav=(f"<nav><a href='index.html'>개요</a>"
         f"<a href='f1.html' class='{'on' if page_id=='f1' else ''}'>F1 검증</a>"
         f"<a href='f4.html' class='{'on' if page_id=='f4' else ''}'>F4 검증</a>"
         f"<a href='glossary.html'>용어사전</a>"
         f"<a href='tau_selection_report.html'>τ 선정 보고서</a></nav>")
    nmerged=sum(1 for c in cards if c['n']>1)
    nhold=sum(1 for c in cards if c.get('em_status')=='hold')
    js=JS_TMPL.replace('__TIER__', page_id)
    page=(f"<!doctype html><html lang=ko><head><meta charset=utf-8><title>{title}</title><style>{CSS}</style></head><body>"
          f"<header><h1>{title}</h1>"
          f"<div class=sub>총 <b>{total}장</b> · L3 {len(byl3)}개 사용 · 통합 그룹 {nmerged}개 · {sub_extra} "
          f"계층 순서: General → Agentic → Physical. "
          f"검수 3기준: <b>① 기술 적절성</b>(카드가 리스크를 올바르게 기술?) · <b>② L3 매핑 적절성</b>(L3 배정이 적절?) · "
          f"<b>③ 타 카드와의 중복성</b>(다른 카드와 중복?). "
          f"L3 배정은 EM(시드 고정 하이브리드) 재수행 결과입니다.</div>{nav}"
          f"<div class=tools><input type=text id=q placeholder='검색: ID / 명칭 / 정의 (한·영)'>"
          f"<button data-f='' class=on>전체</button>"
          f"<button data-f=merged>병합만</button>"
          ""
          f"<button id=expand>전체 펼치기</button><button id=collapse>전체 접기</button>"
          f"<span id=cnt class=sub></span></div></header><main>{body}</main>"
          f"<div id=bbar><span id=ptxt>진행률 0 / {total}</span><div id=pbar><div id=pfill></div></div>"
          f"<button id=exp>판정 JSON 내보내기</button></div>"
          f"<script>{js}</script></body></html>")
    open(f'{OUT}/{page_id}.html','w').write(page)
    print(page_id, total, 'cards,', nmerged, 'merged,', nhold, 'hold,', len(byl3), 'L3')

F1=json.load(open(f'{OUT}/f1_state.json'))
build('f1', F1['cards'],
      'F1 — τ*₁=0.8329 granularity flow 1차 티어 (휴먼 검수)',
      f"τ={F1['tau']:.4f} · 대표 텍스트는 medoid 원문 · L3는 EM 재배정.")

F4=json.load(open(f'{OUT}/flow4_cards_full.json'))
build('f4', F4['cards'],
      'F4 — granularity flow 4차 티어 (휴먼 검수)',
      'τ* 0.8329→0.7753 · L3는 EM 재배정.')
