#!/usr/bin/env python3
import csv, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'07_human_review_recovery_applied'; MASTER=ROOT/'03_outputs/release/L1_L2_L3_Master.csv'
EXPECTED='e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df'; DOM=('General','Agentic','Physical')
HIER=("L0_ID","L0_Title_ko","L0_Title_en","L1_ID","L1_Title_ko","L1_Title_en","L1_Description_ko","L1_Description_en","L2_ID","L2_Title_ko","L2_Title_en","L2_Description_ko","L2_Description_en","L3_ID","L3_Title_ko","L3_Title_en","L3_Description_ko","L3_Description_en")
AI_KO=re.compile(r'AI|인공지능|인공일반지능|알고리즘|에이전트|로봇|휴머노이드|머신러닝|기계학습|모델|LLM',re.I); AI_EN=re.compile(r'\bAI\b|\bAGI\b|artificial intelligence|artificial general intelligence|algorithm|agent|robot|humanoid|machine learning|model|LLM',re.I)
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
 failures=defaultdict(list); mh=hashlib.sha256(MASTER.read_bytes()).hexdigest()
 if mh!=EXPECTED: failures['master_hash'].append(mh)
 masters={r['L3_ID']:r for r in read(MASTER)}; rows=[]
 for d in DOM:
  for r in read(OUT/f'L4_{d}_Human_Review_Recovery_Applied.csv'): r['_domain']=d; rows.append(r)
 ids=[r['L4_ID'] for r in rows]
 failures['duplicate_ids'] += [x for x,n in Counter(ids).items() if n>1]
 by=defaultdict(list)
 for r in rows:
  if 'Others' in r['L3_ID']: failures['others'].append(r['L4_ID'])
  m=masters.get(r['L3_ID'])
  if not m: failures['unknown_l3'].append(r['L4_ID']); continue
  for f in HIER:
   if r.get(f,'')!=m.get(f,''): failures['hierarchy'].append([r['L4_ID'],f])
  if not re.fullmatch(re.escape(r['L3_ID'])+r'_\d{3}',r['L4_ID']): failures['id_format'].append(r['L4_ID'])
  by[r['L3_ID']].append(int(r['L4_ID'].rsplit('_',1)[1]))
  for f in ('L4_Title_ko','L4_Title_en','L4_Description_ko','L4_Description_en','source_row_id'):
   if not r.get(f,'').strip(): failures['blank'].append([r['L4_ID'],f])
  if not AI_KO.search(r['L4_Description_ko']): failures['ai_grounding_ko'].append(r['L4_ID'])
  if not AI_EN.search(r['L4_Description_en']): failures['ai_grounding_en'].append(r['L4_ID'])
 for l3,nums in by.items():
  if sorted(nums)!=list(range(1,len(nums)+1)): failures['continuity'].append(l3)
 dup=Counter((r['L3_ID'],r['L4_Title_ko'].strip(),r['L4_Title_en'].strip()) for r in rows)
 failures['exact_duplicates'] += [list(k) for k,n in dup.items() if n>1]
 ledger=read(OUT/'Source_Disposition_Ledger.csv')
 if len(ledger)!=808: failures['ledger_rows'].append(len(ledger))
 for r in ledger:
  if r['Disposition'] not in ('DELETE','OUTPUT','NO_BASELINE_OUTPUT'): failures['disposition'].append(r['Register_ID'])
  if r['Disposition']=='OUTPUT' and int(r['Output_Count'])<1: failures['lost_source'].append(r['source_row_id'])
 decisions=read(ROOT/'06_human_review_recovery/Human_Review_Round2_Recovery_Decisions.csv')
 if len(decisions)!=166 or any(r['Approval_Status']!='APPROVED_FOR_RECOVERY_20260829' for r in decisions): failures['decisions'].append('invalid')
 report={'status':'PASS' if not any(failures.values()) else 'FAIL','cards':len(rows),'by_domain':dict(Counter(r['_domain'] for r in rows)),'others':len(failures['others']),'l3_master_sha256':mh,'checks':{k:len(v) for k,v in failures.items()},'failure_examples':{k:v[:10] for k,v in failures.items() if v}}
 (OUT/'Recovery_Validation_Record.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2)); sys.exit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()
