# build_pair_survey.py — blinded pair-judgment experiment for merge-precision ceiling
#
# Samples 135 card pairs in four hidden strata, then renders a self-contained
# bilingual survey page. Raters never see stratum, similarity, or flow decision.
#
#   S1  40  merged by the flow at step 1 (crossing boundary)
#   S2  40  merged by the flow at steps 2-5 only
#   S3  40  never merged through step 5, cosine matched to the S2 range
#   S4  15  never merged through step 5, cosine >= 0.86 (hard negatives,
#           includes normatively protected look-alikes)
#
# Outputs
#   data/experiments/review/pair_survey.html      the survey (public)
#   data/experiments/review/pair_survey_key.csv   answer key (NOT committed;
#                                                 its SHA-256 is committed instead)
#   data/experiments/review/pair_survey_key.sha256
#
# Fixed seed; per-rater presentation order is derived from the rater's name.
import json, csv, hashlib, html as H
import numpy as np

SEED = 20260901
rng = np.random.default_rng(SEED)
REV = 'data/experiments/review'

master = json.load(open('data/experiments/stage1/out/master.json'))['cards']
pos = {c['l4_id']: i for i, c in enumerate(master)}
emb = np.load('data/experiments/stage1/out/emb_78d29c0cbe8d.npy')
X = emb / np.linalg.norm(emb, axis=1, keepdims=True)

F1 = json.load(open(f'{REV}/f1_state.json'))['cards']
F5 = json.load(open(f'{REV}/f5_state.json'))['cards']

f1_of = {}
for g in F1:
    for m in g['members']: f1_of[m] = g['rep']
f5_of = {}
for g in F5:
    for m in g['members']: f5_of[m] = g['rep']

def cos(a, b):
    return float(X[pos[a]] @ X[pos[b]])

# ---------------------------------------------------------------- S1 and S2
s1_pool, s2_pool = [], []
for g in F5:
    mem = g['members']
    if len(mem) < 2: continue
    for i in range(len(mem)):
        for j in range(i + 1, len(mem)):
            a, b = mem[i], mem[j]
            if f1_of[a] == f1_of[b]:
                s1_pool.append((a, b))
            else:
                s2_pool.append((a, b))
rng.shuffle(s1_pool); rng.shuffle(s2_pool)

def take(pool, k, used):
    out = []
    for a, b in pool:
        if a in used or b in used: continue   # one appearance per card
        out.append((a, b)); used.add(a); used.add(b)
        if len(out) == k: break
    return out

used = set()
S1 = take(s1_pool, 40, used)
S2 = take(s2_pool, 40, used)

# ------------------------------------------------- S3 (cos-matched) and S4
s2_cos = [cos(a, b) for a, b in S2]
lo, hi = min(s2_cos), max(s2_cos)

S = (X @ X.T).astype(np.float32)
np.fill_diagonal(S, -1)
iu = np.triu_indices(len(master), 1)
vals = S[iu]

ids = [c['l4_id'] for c in master]
same5 = np.zeros(len(vals), bool)
# mark pairs that share an F5 group
rep_idx = {}
for g in F5:
    gi = [pos[m] for m in g['members']]
    for i in gi:
        rep_idx[i] = g['rep']
pair_same = np.array([rep_idx.get(int(i)) == rep_idx.get(int(j))
                      for i, j in zip(iu[0], iu[1])])

m3 = (~pair_same) & (vals >= lo) & (vals <= hi)
idx3 = np.where(m3)[0]; rng.shuffle(idx3)
# S4: the hardest negatives that exist — the highest-cosine pairs the flow
# still kept apart through step 5 (by step 5 nearly everything above 0.86 has
# merged, so these sit just below the current boundary).
idx4 = np.where(~pair_same)[0]
idx4 = idx4[np.argsort(-vals[idx4])]          # descending cosine, no shuffle

def take_idx(idxs, k, used):
    out = []
    for t in idxs:
        a, b = ids[int(iu[0][t])], ids[int(iu[1][t])]
        if a in used or b in used: continue
        out.append((a, b)); used.add(a); used.add(b)
        if len(out) == k: break
    return out

S4 = take_idx(idx4, 15, used)          # hard negatives first (rarer)
S3 = take_idx(idx3, 40, used)

pairs = ([('S1', p) for p in S1] + [('S2', p) for p in S2] +
         [('S3', p) for p in S3] + [('S4', p) for p in S4])
rng.shuffle(pairs)                      # base order also randomized

# ------------------------------------------------------------ key (private)
with open(f'{REV}/pair_survey_key.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['pair_id', 'stratum', 'card_a', 'card_b', 'cosine',
                'flow_merged_by_step5', 'merged_at_step1'])
    for k, (st, (a, b)) in enumerate(pairs, 1):
        w.writerow([f'P{k:03d}', st, a, b, f'{cos(a,b):.4f}',
                    'yes' if st in ('S1', 'S2') else 'no',
                    'yes' if st == 'S1' else 'no'])
sha = hashlib.sha256(open(f'{REV}/pair_survey_key.csv', 'rb').read()).hexdigest()
open(f'{REV}/pair_survey_key.sha256', 'w').write(
    sha + '  pair_survey_key.csv\n')

# ------------------------------------------------------------------ survey
def esc(s): return H.escape(s or '')
by = {c['l4_id']: c for c in master}

items = []
for k, (st, (a, b)) in enumerate(pairs, 1):
    ca, cb = by[a], by[b]
    items.append(dict(
        id=f'P{k:03d}',
        a=dict(ko=ca['label_ko'], en=ca['label_en'],
               dko=ca['definition_ko'], den=ca['definition_en']),
        b=dict(ko=cb['label_ko'], en=cb['label_en'],
               dko=cb['definition_ko'], den=cb['definition_en'])))

DATA = json.dumps(items, ensure_ascii=False)

page = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Merge-precision pair judgment survey</title><style>
*{box-sizing:border-box}
body{font-family:'Apple SD Gothic Neo','Noto Sans KR',-apple-system,sans-serif;margin:0;color:#1c1c1c;background:#fafaf8}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:12px 20px;z-index:20}
h1{font-size:17px;margin:0 0 4px}
.sub{color:#555;font-size:12.5px;line-height:1.7}
main{max-width:860px;margin:0 auto;padding:16px 20px 90px}
.intro{border:1px solid #d8d2c2;background:#fbf9f3;border-radius:8px;padding:12px 16px;font-size:13px;line-height:1.85;margin:12px 0}
.intro b{color:#1f5c46}
.rater{display:flex;gap:8px;align-items:center;margin:14px 0}
.rater input{padding:6px 10px;font-size:14px;border:1px solid #bbb;border-radius:5px;width:260px}
.rater button{padding:6px 14px;border:1px solid #0f6e56;background:#0f6e56;color:#fff;border-radius:5px;cursor:pointer;font-size:13px}
.pair{border:1px solid #ddd;border-radius:8px;background:#fff;padding:14px 16px;margin:14px 0}
.pid{font-size:11.5px;color:#999;font-family:ui-monospace,monospace}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0}
.card{border:1px solid #e8e8e4;border-radius:6px;padding:10px 12px;background:#fcfcfb}
.card h4{margin:0 0 2px;font-size:13.5px}
.card .en{font-size:11.5px;color:#777;margin:0 0 6px}
.card p{font-size:12.5px;line-height:1.75;margin:4px 0;color:#333}
.card p.den{color:#888;font-size:11.5px}
.judge{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:13px}
.judge label{cursor:pointer;padding:4px 10px;border:1px solid #ccc;border-radius:14px}
.judge input{margin-right:5px}
.judge label:has(input:checked){background:#0f6e56;color:#fff;border-color:#0f6e56}
.memo{width:100%;margin-top:8px;padding:5px 9px;font-size:12.5px;border:1px solid #ddd;border-radius:4px}
#bbar{position:fixed;left:0;right:0;bottom:0;background:#2a2a2a;color:#eee;font-size:12.5px;padding:9px 18px;display:flex;gap:14px;align-items:center;z-index:30;box-shadow:0 -2px 10px rgba(0,0,0,.18)}
#bbar button{background:#0f6e56;color:#fff;border:none;padding:5px 12px;border-radius:4px;cursor:pointer}
#pbar{flex:0 0 200px;height:8px;background:#555;border-radius:4px;overflow:hidden}
#pfill{height:100%;width:0;background:#7dd3b0}
.savemsg{color:#9a9a9a;font-size:12px}
@media(max-width:640px){.cards{grid-template-columns:1fr}}
</style></head><body>
<header><h1>리스크 카드 쌍 판정 · Merge-precision pair judgment</h1>
<div class=sub>두 카드가 <b>같은 리스크의 다른 표현</b>인지, <b>서로 구별되는 리스크</b>인지 판정합니다.
카드 출처·유사도·알고리즘 판정은 공개되지 않습니다(맹검). 순서는 판정자마다 다르게 제시됩니다. 완료 후 <b>제출</b>을 누르면 응답이 즉시 서버에 누적 저장됩니다(계정 불필요). 같은 이름으로 다시 제출하면 최신본이 사용됩니다.</div>
</header><main>

<div class=intro>
<b>판정 기준.</b> 두 카드가 <b>같은 해악 기제와 같은 해악 결과</b>를 같은 추상 수준에서 기술하면
"같은 리스크"입니다. 문구·표현·언어의 차이는 무시하십시오. 다음은 <b>다른 리스크</b>로 판정합니다:
기제만 같고 결과가 다른 경우, 결과만 같고 기제가 다른 경우, 하나가 일반 구성개념이고 다른 하나가
특정 맥락 사례인 경우(추상 수준 상이), 규범적으로 분리 유지가 요구되는 경우.
확신이 서지 않으면 "판단 불가"를 고르고 메모를 남겨 주십시오.<br>
<b>Criterion.</b> Two cards are the <b>same risk</b> when they describe the same harm mechanism and the
same harm outcome at the same level of abstraction; ignore differences of wording or language.
Judge them <b>distinct</b> when only the mechanism or only the outcome coincides, when one is a general
construct and the other a context-bound instance, or when normative considerations require separation.
If unsure, choose "cannot decide" and leave a note.
</div>

<div class=rater>
<label for=rname style="font-size:13px">판정자 이름 (실명) · Rater name:</label>
<input id=rname type=text placeholder="e.g. Youngsam Chun">
<button id=rstart>시작 · Start</button>
<span id=rmsg class=sub></span>
</div>

<div id=list></div>
</main>
<div id=bbar><span id=ptxt>0 / 0</span><div id=pbar><div id=pfill></div></div>
<button id=submit>제출 · Submit</button>
<button id=exp style="background:#3a6ea5">Export JSON (backup)</button>
<label for=impf style="padding:4px 10px;border:1px solid #888;border-radius:4px;background:#3a3a3a;cursor:pointer">Import JSON</label>
<input id=impf type=file accept=".json" hidden>
<span id=save class=savemsg></span></div>
<script>
const ITEMS=__DATA__;
let RATER=localStorage.getItem('pair_rater')||'';
const KEY=()=> 'pair_survey_'+RATER;

function hash(s){let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0}
function order(name){
  const idx=[...ITEMS.keys()];const h=hash(name.trim().toLowerCase()||'x');
  let s=h; const rnd=()=>{s^=s<<13;s^=s>>>17;s^=s<<5;s>>>=0;return s/4294967296};
  for(let i=idx.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));[idx[i],idx[j]]=[idx[j],idx[i]]}
  return idx;
}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML}
function render(){
  const list=document.getElementById('list');list.innerHTML='';
  if(!RATER){document.getElementById('rmsg').textContent='이름을 입력하고 시작을 누르십시오.';return}
  document.getElementById('rname').value=RATER;
  document.getElementById('rmsg').textContent='판정자: '+RATER;
  for(const t of order(RATER)){
    const it=ITEMS[t];
    const div=document.createElement('div');div.className='pair';div.dataset.id=it.id;
    div.innerHTML='<span class=pid>'+it.id+'</span>'
     +'<div class=cards>'
     +'<div class=card><h4>'+esc(it.a.ko)+'</h4><p class=en>'+esc(it.a.en)+'</p><p>'+esc(it.a.dko)+'</p><p class=den>'+esc(it.a.den)+'</p></div>'
     +'<div class=card><h4>'+esc(it.b.ko)+'</h4><p class=en>'+esc(it.b.en)+'</p><p>'+esc(it.b.dko)+'</p><p class=den>'+esc(it.b.den)+'</p></div>'
     +'</div><div class=judge>'
     +'<label><input type=radio name=j_'+it.id+' value=same>같은 리스크 · Same risk</label>'
     +'<label><input type=radio name=j_'+it.id+' value=distinct>다른 리스크 · Distinct risks</label>'
     +'<label><input type=radio name=j_'+it.id+' value=undecided>판단 불가 · Cannot decide</label>'
     +'</div><input class=memo placeholder="메모 (선택) · Note (optional)">';
    list.appendChild(div);
  }
  restore(); prog();
}
function collect(){
  const out={rater:RATER,saved_at:new Date().toISOString(),survey_sha:'__SHA__',judgments:[]};
  document.querySelectorAll('.pair').forEach(p=>{
    const id=p.dataset.id;
    const v=p.querySelector('input[name=j_'+id+']:checked');
    const m=p.querySelector('.memo').value;
    if(v||m)out.judgments.push({pair:id,verdict:v?v.value:null,note:m||''});
  });
  return out;
}
function stamp(m){document.getElementById('save').textContent=m}
let timer=null;
function save(){clearTimeout(timer);timer=setTimeout(()=>{try{
  const d=collect();localStorage.setItem(KEY(),JSON.stringify(d));
  stamp('Saved '+new Date().toLocaleTimeString()+' · '+d.judgments.length+' judged');
}catch(e){stamp('Autosave unavailable — export before closing')}},400)}
function restore(){
  try{const raw=localStorage.getItem(KEY());if(!raw)return;
    const d=JSON.parse(raw);
    d.judgments.forEach(j=>{
      const p=document.querySelector('.pair[data-id='+j.pair+']');if(!p)return;
      if(j.verdict){const e=p.querySelector('input[name=j_'+j.pair+'][value='+j.verdict+']');if(e)e.checked=true}
      if(j.note)p.querySelector('.memo').value=j.note;
    });
    stamp('Restored '+d.judgments.length+' judgments');
  }catch(e){}
}
function prog(){
  const n=document.querySelectorAll('.pair').length;
  const d=[...document.querySelectorAll('.pair')].filter(p=>p.querySelector('input:checked')).length;
  document.getElementById('ptxt').textContent=d+' / '+n;
  document.getElementById('pfill').style.width=(n?100*d/n:0)+'%';
}
document.getElementById('rstart').onclick=()=>{
  const v=document.getElementById('rname').value.trim();
  if(!v){alert('실명을 입력해 주십시오.');return}
  RATER=v;localStorage.setItem('pair_rater',v);render();
};
document.addEventListener('change',e=>{if(e.target.matches('input')){save();prog()}});
document.addEventListener('input',e=>{if(e.target.matches('.memo'))save()});
document.getElementById('exp').onclick=()=>{
  const d=collect();
  const blob=new Blob([JSON.stringify(d,null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download='pair_judgments_'+(RATER||'anon').replace(/\\s+/g,'_')+'_'+new Date().toISOString().slice(0,10)+'.json';
  a.click();stamp('Exported');
};

const REPO='deep1003/RAI-Risk-Taxonomy-2.0';
let ENDPOINT='';
fetch('survey_endpoint.txt',{cache:'no-store'}).then(r=>r.text()).then(t=>{
  t=t.trim(); if(t&&t.startsWith('https://')) ENDPOINT=t;
}).catch(()=>{});
function compact(){
  const map={same:'s',distinct:'d',undecided:'u'};
  const v=Array(ITEMS.length).fill('-'); const notes={};
  const d=collect();
  d.judgments.forEach(j=>{
    const k=parseInt(j.pair.slice(1),10)-1;
    if(j.verdict)v[k]=map[j.verdict]||'-';
    if(j.note)notes[j.pair]=j.note;
  });
  return {rater:d.rater,saved_at:d.saved_at,survey_sha:d.survey_sha,
          verdicts:v.join(''),notes:notes};
}
function issueBody(c){
  return '### Pair-judgment submission\\n\\n'
   +'- rater: '+c.rater+'\\n- saved_at: '+c.saved_at+'\\n- survey_sha: '+c.survey_sha+'\\n\\n'
   +'```json\\n'+JSON.stringify(c,null,1)+'\\n```\\n';
}
function submitViaIssue(c){
  const body=issueBody(c);
  const url='https://github.com/'+REPO+'/issues/new'
   +'?title='+encodeURIComponent('[pair-judgments] '+c.rater)
   +'&labels=pair-judgments&body='+encodeURIComponent(body);
  if(url.length<7500){window.open(url,'_blank');
    stamp('GitHub \uc774\uc288 \ucc3d\uc774 \uc5f4\ub9bd\ub2c8\ub2e4 \u2014 Submit new issue\ub97c \ub204\ub974\uba74 \uc644\ub8cc');}
  else{try{navigator.clipboard.writeText(body);}catch(e){}
    window.open('https://github.com/'+REPO+'/issues/new?title='
      +encodeURIComponent('[pair-judgments] '+c.rater)+'&labels=pair-judgments','_blank');
    stamp('\ubcf8\ubb38\uc744 \uc774\uc288\uc5d0 \ubd99\uc5ec\ub123\uc73c\uc2ed\uc2dc\uc624 (\ud074\ub9bd\ubcf4\ub4dc\uc5d0 \ubcf5\uc0ac\ub428)');}
}
document.getElementById('submit').onclick=async()=>{
  const c=compact();
  const done=[...c.verdicts].filter(x=>x!=='-').length;
  if(done<ITEMS.length&&!confirm(done+' / '+ITEMS.length+' \ud310\uc815\ub428. \uadf8\ub798\ub3c4 \uc81c\ucd9c\ud560\uae4c\uc694?'))return;
  const btn=document.getElementById('submit');
  if(ENDPOINT){
    btn.disabled=true;btn.textContent='\uc800\uc7a5 \uc911\u2026';
    try{
      const r=await fetch(ENDPOINT,{method:'POST',
        headers:{'Content-Type':'text/plain;charset=utf-8'},
        body:JSON.stringify(c)});
      const res=await r.json();
      if(res.ok){btn.textContent='\uc81c\ucd9c \uc644\ub8cc \u2713';
        stamp('\uc800\uc7a5\ub428 \u2014 \ub204\uc801 '+res.rows+'\uac74. \uc218\uc815 \ud6c4 \ub2e4\uc2dc \uc81c\ucd9c\ud574\ub3c4 \ub429\ub2c8\ub2e4(\ucd5c\uc2e0\ubcf8 \uc0ac\uc6a9).');
        return;}
      throw new Error(res.error||'server error');
    }catch(err){
      btn.disabled=false;btn.textContent='GitHub\uc73c\ub85c \uc81c\ucd9c \u00b7 Submit';
      stamp('\uc11c\ubc84 \uc800\uc7a5 \uc2e4\ud328('+err.message+') \u2014 GitHub \uc774\uc288\ub85c \uc804\ud658\ud569\ub2c8\ub2e4');
      submitViaIssue(c);return;
    }
  }
  submitViaIssue(c);
};
document.getElementById('impf').addEventListener('change',e=>{
  const f=e.target.files[0];if(!f)return;const rd=new FileReader();
  rd.onload=()=>{try{const d=JSON.parse(rd.result);
    if(d.rater){RATER=d.rater;localStorage.setItem('pair_rater',RATER)}
    localStorage.setItem(KEY(),JSON.stringify(d));render();stamp('Imported '+d.judgments.length);
  }catch(err){stamp('Could not read file')}};
  rd.readAsText(f);
});
if(RATER)render(); else prog();
</script></body></html>"""

page = page.replace('__DATA__', DATA).replace('__SHA__', sha[:16])
open(f'{REV}/pair_survey.html', 'w', encoding='utf-8').write(page)

from collections import Counter
strata = Counter(st for st, _ in pairs)
print('pairs:', len(pairs), dict(strata))
print('S2 cosine range: %.3f-%.3f' % (lo, hi))
print('key sha256:', sha)
