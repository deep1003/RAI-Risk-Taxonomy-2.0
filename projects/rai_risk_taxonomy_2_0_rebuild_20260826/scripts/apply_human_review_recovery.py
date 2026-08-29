#!/usr/bin/env python3
"""Apply the approved 2026-08-29 human-review recovery decisions.

This is a deterministic lineage overlay. It does not run EM or create L3s.
"""
from __future__ import annotations

import csv, hashlib, json, re, shutil
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "05_human_review_round2"
REC = ROOT / "06_human_review_recovery"
OUT = ROOT / "07_human_review_recovery_applied"
MASTER = ROOT / "03_outputs/release/L1_L2_L3_Master.csv"
EXPECTED_MASTER_HASH = "e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df"
DOMAINS = ("General", "Agentic", "Physical")
L1_DOMAIN = {"L1_G":"General", "L1_A":"Agentic", "L1_P":"Physical"}
HIER = ("L0_ID","L0_Title_ko","L0_Title_en","L1_ID","L1_Title_ko","L1_Title_en","L1_Description_ko","L1_Description_en","L2_ID","L2_Title_ko","L2_Title_en","L2_Description_ko","L2_Description_en","L3_ID","L3_Title_ko","L3_Title_en","L3_Description_ko","L3_Description_en")
STALE = ("EM_Score","EM_Margin","EM_Stability","EM_Anchor_Score","Hybrid_EM_Score","Hybrid_EM_Margin","L4_Keyword_1_ko","L4_Keyword_2_ko","L4_Keyword_3_ko","L4_Keyword_1_en","L4_Keyword_2_en","L4_Keyword_3_en","Keyword_Top_L3_ID","Keyword_Support_Score","Keyword_Semantic_Score","Keyword_Prior","Keyword_Evidence","Candidate_1_L3_ID","Candidate_1_EM_Score","Candidate_1_Hybrid_Score","Candidate_2_L3_ID","Candidate_2_EM_Score","Candidate_2_Hybrid_Score","KO_Top_L3_ID","EN_Top_L3_ID","Candidate_Constraint_Reason","Definition_L3_Anchor_ID","Definition_L3_Anchor_Score","Definition_Grounding_Action")

def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
def toks(s): return [x.strip() for x in re.split(r"[;|,]",s or "") if x.strip()]
def union(rows, field): return ";".join(dict.fromkeys(x for r in rows for x in toks(r.get(field,""))))
def append(old, new): return "|".join(dict.fromkeys(toks(old)+[new]))

SPLIT_TEXT = {
"SRC-G-0047": {
 "G_INT_REPR": ("집단 고정관념의 재현과 강화","Representation and reinforcement of group stereotypes","AI 시스템이 학습 데이터에 포함된 집단 고정관념을 출력에 재현하거나 강화하여 해당 집단에 대한 왜곡되고 적대적인 표상을 확산하는 리스크.","The risk that an AI system reproduces or reinforces group stereotypes embedded in training data, thereby propagating distorted or hostile representations of the affected group."),
 "G_INT_ALLOC": ("집단별 성능 격차에 따른 차별적 결과","Discriminatory outcomes from group performance disparities","AI 시스템의 집단별 성능 격차가 자원, 기회, 서비스 또는 접근의 불리한 배분으로 이어지는 리스크.","The risk that disparities in an AI system's performance across groups lead to unequal allocation of resources, opportunities, services, or access."),},
"SRC-G-0458": {
 "G_INT_ALLOC": ("콘텐츠 조정에 의한 집단별 접근 제한","Group-based access restriction through content moderation","AI 기반 콘텐츠 조정 시스템이 특정 집단의 콘텐츠 노출, 게시 또는 서비스 접근을 불균형하게 제한하는 리스크.","The risk that an AI-based content moderation system disproportionately restricts a group's content visibility, publication, or access to services."),
 "G_INT_REPR": ("콘텐츠 조정에 의한 집단 표상 왜곡","Distortion of group representation through content moderation","AI 기반 콘텐츠 조정 시스템이 특정 집단의 관점과 표현을 선택적으로 억제하여 사회적 표상을 왜곡하는 리스크.","The risk that an AI-based content moderation system selectively suppresses a group's perspectives and expression, distorting its social representation."),
 "G_INT_UNETH": ("콘텐츠 조정에 의한 여론 조작","Manipulation of public discourse through content moderation","AI 기반 콘텐츠 조정 시스템이 정보의 노출과 도달 범위를 은밀하게 조정하여 이용자의 판단이나 공적 담론을 조작하는 리스크.","The risk that an AI-based content moderation system covertly controls information visibility and reach to manipulate user judgement or public discourse."),},
"SRC-G-0343": {
 "G_INT_REPR": ("편향된 표상의 반복 증폭","Recursive amplification of biased representations","AI 시스템이 편향된 입력과 출력을 반복적으로 학습하거나 추천하여 특정 집단에 대한 왜곡된 표상을 증폭하는 리스크.","The risk that an AI system repeatedly learns from or recommends biased inputs and outputs, amplifying distorted representations of particular groups."),
 "G_SOC_CULT": ("AI 생성 결과의 문화적 획일화","Cultural homogenisation of AI-generated outputs","AI 시스템이 지배적인 언어와 문화의 표현을 우선하여 다양한 문화적 지식과 관점의 가시성 및 지속성을 약화하는 리스크.","The risk that an AI system privileges dominant linguistic and cultural expressions, weakening the visibility and continuity of diverse cultural knowledge and perspectives."),},
"SRC-G-0487": {
 "G_INT_ALLOC": ("체계적 편향에 의한 집단 배제","Group exclusion through systematic bias","AI 시스템의 체계적 편향이 특정 집단의 자원, 기회, 서비스 또는 접근을 지속적으로 제한하는 리스크.","The risk that systematic bias in an AI system persistently restricts a particular group's access to resources, opportunities, services, or participation."),
 "G_INT_SEX": ("체계적 편향에 의한 성적 위해와 착취","Sexual harm and exploitation through systematic bias","AI 시스템의 체계적 편향이 특정 집단을 대상으로 성적 대상화, 성적 학대 또는 착취를 생성하거나 조장하는 리스크.","The risk that systematic bias in an AI system generates or facilitates sexual objectification, abuse, or exploitation targeting a particular group."),},
"SRC-G-0170": {
 "G_SYS_TRANS": ("AI 제품 역량의 오도성 표시","Misleading representation of AI product capabilities","AI 제공자가 AI 시스템의 기능, 한계 또는 검증 범위를 불명확하거나 오도되게 표시하여 이용자의 합리적 판단을 저해하는 리스크.","The risk that an AI provider presents an AI system's functions, limitations, or validation scope in an unclear or misleading manner, impairing informed user judgement."),
 "G_SYS_OEXT": ("검증 범위를 초과한 AI 기능 사용","Use of AI functions beyond validated scope","AI 시스템이 검증된 기능과 운용 범위를 넘어 사용되어 제품 기능 실패와 후속 피해를 초래하는 리스크.","The risk that an AI system is used beyond its validated functions and operating scope, causing product failure and resulting harm."),},
"SRC-G-0244": {
 "G_INT_PRIV": ("AI 기반 불법적 대중 감시","Unlawful AI-enabled mass surveillance","AI 시스템이 적법한 근거, 필요성 또는 비례성 없이 대규모 개인 식별, 추적 또는 행동 감시에 사용되어 사생활과 개인정보를 침해하는 리스크.","The risk that an AI system is used for large-scale identification, tracking, or behavioural surveillance without a lawful basis, necessity, or proportionality, infringing privacy and personal data rights."),
 "G_SOC_DEMOC": ("AI 기반 검열과 공적 담론 억압","AI-enabled censorship and suppression of public discourse","AI 시스템이 표현과 정보 접근을 광범위하게 차단하거나 선별하여 공적 담론과 민주적 참여를 억압하는 리스크.","The risk that an AI system broadly blocks or filters expression and access to information, suppressing public discourse and democratic participation."),},
"SRC-G-0142": {
 "G_SYS_TRANS": ("AI 상호작용의 불충분한 고지","Inadequate disclosure in AI interaction","AI 시스템이 이용자에게 AI와 상호작용하고 있다는 사실, 기능, 한계 또는 결과의 근거를 충분히 고지하지 않아 정보에 기반한 판단을 저해하는 리스크.","The risk that an AI system fails to adequately disclose the fact of AI interaction, its functions, limitations, or the basis of its outputs, impairing informed judgement."),
 "G_INT_PRIV": ("AI 데이터 처리에 대한 유효한 동의 결여","Lack of valid consent for AI data processing","AI 시스템이 개인 데이터의 수집, 이용 또는 공유에 관하여 자유롭고 구체적이며 충분한 정보에 기반한 동의 없이 처리하는 리스크.","The risk that an AI system collects, uses, or shares personal data without consent that is freely given, specific, and informed."),},
"SRC-G-0255": {
 "G_INT_COPY": ("AI를 이용한 저작물 도용","Misappropriation of copyrighted works using AI","AI 시스템이 권리자의 허락이나 적법한 근거 없이 저작물을 복제, 변형 또는 배포하여 저작권을 침해하는 리스크.","The risk that an AI system reproduces, transforms, or distributes copyrighted works without authorisation or a lawful basis, infringing copyright."),
 "G_INT_PRIV": ("AI를 이용한 개인정보 도용과 착취","Identity and personal data exploitation using AI","AI 시스템이 개인의 신원정보나 개인정보를 무단으로 취득, 결합 또는 이용하여 사칭, 착취 또는 사생활 침해를 초래하는 리스크.","The risk that an AI system unlawfully acquires, combines, or uses identity information or personal data, causing impersonation, exploitation, or privacy infringement."),},
"SRC-G-0056": {
 "G_INT_UNETH": ("맥락 순응형 아첨에 의한 판단 조작","Manipulation of judgement through context-compliant sycophancy","AI 시스템이 이용자의 선호나 전제에 맞추어 사실성과 무관하게 동조하는 답변을 생성하여 이용자의 판단을 조작하는 리스크.","The risk that an AI system produces agreeable responses aligned with a user's preferences or premises regardless of truthfulness, manipulating user judgement."),
 "G_SYS_MISINFO": ("맥락 일관성 추구에 의한 환각 증폭","Amplification of hallucinations through context consistency","AI 시스템이 대화 맥락의 일관성을 우선하여 앞선 오류나 근거 없는 주장을 반복하고 확대함으로써 허위정보를 생성하는 리스크.","The risk that an AI system prioritises conversational consistency and repeats or expands earlier errors or unsupported claims, generating misinformation."),},
"SRC-G-0119": {
 "G_SYS_EVAL": ("AI 모델 설정과 평가의 부적절성","Inadequate AI model configuration and evaluation","AI 시스템의 설정, 시험 또는 성능 평가가 사용 맥락과 위험 수준에 적합하지 않아 결함이 탐지되지 않는 리스크.","The risk that an AI system's configuration, testing, or performance evaluation is unsuitable for its context of use and level of risk, leaving defects undetected."),
 "G_SYS_OVERCONF": ("정량화되지 않은 예측 불확실성","Unquantified predictive uncertainty","AI 시스템이 예측 불확실성을 적절히 산정하거나 전달하지 않아 이용자가 출력의 신뢰도를 과대평가하는 리스크.","The risk that an AI system fails to estimate or communicate predictive uncertainty adequately, causing users to overestimate the reliability of its outputs."),},
"SRC-G-0196": {
 "G_SYS_SECADV": ("샌드박스 우회에 의한 격리 통제 상실","Loss of isolation control through sandbox escape","AI 시스템 또는 그 실행 코드가 샌드박스의 격리 경계를 우회하여 보호된 자원과 외부 시스템에 무단 접근하는 리스크.","The risk that an AI system or its executed code bypasses sandbox isolation boundaries and gains unauthorised access to protected resources or external systems."),
 "A_SYS_DECEPT": ("격리 통제 회피를 위한 기만적 행동","Deceptive behaviour to evade isolation controls","AI 에이전트가 감시 또는 격리 통제를 회피하기 위해 의도, 상태 또는 행동을 은폐하거나 기만적으로 표시하는 리스크.","The risk that an AI agent conceals or misrepresents its intentions, state, or actions to evade monitoring or isolation controls."),},
"SRC-P-0196": {
 "G_INT_ILLEGAL": ("AI 에이전트를 이용한 불법 행위 수행","Illegal conduct using AI agents","악의적 행위자가 AI 에이전트의 자동화 역량을 이용하여 불법 행위를 계획, 지원 또는 대규모로 실행하는 리스크.","The risk that malicious actors use the automation capabilities of AI agents to plan, support, or execute illegal conduct at scale."),
 "A_SYS_AUTH": ("무감독 AI 에이전트의 과도한 행위 권한","Excessive action authority of unsupervised AI agents","AI 에이전트가 적절한 인간 감독, 승인 또는 권한 제한 없이 도구와 시스템을 조작하고 현실 세계의 행위를 수행하는 리스크.","The risk that an AI agent operates tools and systems or performs real-world actions without adequate human oversight, approval, or limits on authority."),},
}

def apply_l3(row, master):
    for f in HIER: row[f]=master[f]
    for f in STALE: row[f]=""
    row["Mapping_Method"]="HD"; row["HD_Reason"]="HUMAN_REVIEW_ROUND2_RECOVERY"
    row["Domain_Route_Basis"]="HUMAN_REVIEW_ROUND2"
    row["Transformation_Action"]=append(row.get("Transformation_Action",""),"HUMAN_REVIEW_ROUND2_RECOVERY")
    row["Transformation_Rationale"]=(row.get("Transformation_Rationale","")+" | Second-round human-review instruction applied without EM.").strip(" |")

def main():
    assert hashlib.sha256(MASTER.read_bytes()).hexdigest()==EXPECTED_MASTER_HASH
    master_rows=read(MASTER); masters={r["L3_ID"]:r for r in master_rows}
    reg={r["Register_ID"]:r for r in read(REC/"Human_Review_Instruction_Register.csv")}
    decisions=read(REC/"Human_Review_Round2_Recovery_Decisions.csv")
    rows=[]; fields=None
    for d in DOMAINS:
        rr=read(BASE/f"L4_{d}_Human_Review_Round2_Applied.csv"); fields=fields or list(rr[0]); rows+=rr
    for i,r in enumerate(rows): r["_key"]=f"K{i:04d}"
    deleted_sources=set(); edges=[]; tomb=[]; decision_log=[]
    def matches(src): return [r for r in rows if src in toks(r.get("source_row_id","")) and not r.get("_deleted")]
    # Delete first, but retain shared rows after removing only the deleted lineage token.
    for dec in decisions:
        if dec["Final_Action"]!="DELETE": continue
        src=reg[dec["Register_ID"]]["source_row_id"]; deleted_sources.add(src); mm=matches(src)
        for r in mm:
            ss=toks(r.get("source_row_id",""))
            if len(ss)==1: r["_deleted"]="1"; tomb.append({"Register_ID":dec["Register_ID"],"source_row_id":src,"Deleted_L4_ID":r["L4_ID"],"Title_ko":r["L4_Title_ko"],"Reason":dec["Reviewer_Note"]})
            else: r["source_row_id"]=";".join(x for x in ss if x!=src)
        decision_log.append({"Register_ID":dec["Register_ID"],"Action":"DELETE","Status":"APPLIED" if mm else "ALREADY_DELETED","Output_Keys":""})
    # Merge by source lineage. When representative equals source, retain as representative.
    for dec in decisions:
        if dec["Final_Action"]!="MERGE": continue
        src=reg[dec["Register_ID"]]["source_row_id"]; rep=dec["Final_Merge_Representative_source_row_id"] or src
        sm=matches(src); rm=matches(rep)
        targets=toks(dec["Final_Target_L3_IDs"])
        kept=[]
        for target in targets:
            candidates=[r for r in rm if r["L3_ID"]==target] or [r for r in sm if r["L3_ID"]==target]
            if not candidates:
                base=(rm or sm)[0] if (rm or sm) else None
                if not base: continue
                nr=deepcopy(base); nr["_key"]+=f"M{target}"; apply_l3(nr,masters[target]); rows.append(nr); candidates=[nr]
            k=candidates[0]; contributors=list(dict.fromkeys(r["_key"] for r in sm+rm))
            cr=[r for r in rows if r["_key"] in contributors]
            k["source_row_id"]=union(cr,"source_row_id"); k["Source_L4_IDs"]=union(cr,"Source_L4_IDs"); k["facet"]=union(cr,"facet"); k["act-type"]=union(cr,"act-type")
            apply_l3(k,masters[target]); kept.append(k["_key"])
            for r in cr:
                if r["_key"]!=k["_key"] and r["L3_ID"]==target: r["_deleted"]="1"
        for r in list(dict.fromkeys(r["_key"] for r in sm+rm)):
            candidate=next(x for x in rows if x["_key"]==r)
            if candidate["_key"] not in kept: candidate["_deleted"]="1"
        decision_log.append({"Register_ID":dec["Register_ID"],"Action":"MERGE","Status":"APPLIED","Output_Keys":"|".join(kept)})
    # Split and remap/rewrite.
    for dec in decisions:
        act=dec["Final_Action"]
        if act in ("DELETE","MERGE"): continue
        src=reg[dec["Register_ID"]]["source_row_id"]; mm=matches(src); targets=toks(dec["Final_Target_L3_IDs"])
        out=[]
        if act=="SPLIT":
            existing={r["L3_ID"]:r for r in mm if r["L3_ID"] in targets}
            template=mm[0] if mm else None
            if not template: raise RuntimeError(f"No split template for {src}")
            for target in targets:
                r=existing.get(target)
                if r is None:
                    r=deepcopy(template); r["_key"]+=f"S{target}"; rows.append(r)
                apply_l3(r,masters[target])
                if src in SPLIT_TEXT and target in SPLIT_TEXT[src]:
                    r["L4_Title_ko"],r["L4_Title_en"],r["L4_Description_ko"],r["L4_Description_en"]=SPLIT_TEXT[src][target]
                r["Transformation_Action"]=append(r["Transformation_Action"],"HUMAN_REVIEW_SPLIT")
                out.append(r["_key"])
            for r in mm:
                if r["_key"] not in out: r["_deleted"]="1"
        else:
            if not mm: raise RuntimeError(f"No output for {src} {act}")
            # A single-target human decision supersedes older duplicate lineage outputs.
            target=targets[0]; preferred=next((r for r in mm if r["L3_ID"]==target),mm[0])
            apply_l3(preferred,masters[target]); out=[preferred["_key"]]
            for r in mm:
                if r["_key"]!=preferred["_key"]: r["_deleted"]="1"
        decision_log.append({"Register_ID":dec["Register_ID"],"Action":act,"Status":"APPLIED","Output_Keys":"|".join(out)})
    final=[r for r in rows if not r.get("_deleted")]
    grounding_fixes={
      "SRC-G-0072":"The risk that an AI system's reinforcement learning from human feedback overfits to a narrow rater population and converts contested values into a single behavioural norm.",
      "SRC-G-0356":"The risk that, as AI system autonomy increases, people feel less moral responsibility for decisions involving life and death.",
      "SRC-G-0012":"The risk that an AI agent's reinforcement learning policy achieves task reward while violating explicit safety constraints represented as costs or limits.",
    }
    for r in final:
        for src,text in grounding_fixes.items():
            if src in toks(r.get("source_row_id","")): r["L4_Description_en"]=text
    # All source-review Others must have been dispositioned; any residual Others is blocking.
    residual=[r for r in final if "Others" in r["L3_ID"]]
    if residual: raise RuntimeError(f"Residual Others: {[(r['L4_ID'],r['source_row_id']) for r in residual[:10]]} total={len(residual)}")
    # Reissue deterministic contiguous IDs and build lineage edges.
    final.sort(key=lambda r:(r["L1_ID"],r["L3_ID"],r["L4_Title_en"],r["_key"]))
    counts=defaultdict(int)
    for r in final:
        counts[r["L3_ID"]]+=1; r["L4_ID"]=f"{r['L3_ID']}_{counts[r['L3_ID']]:03d}"
        for src in toks(r.get("source_row_id","")): edges.append({"source_row_id":src,"L4_ID":r["L4_ID"],"L3_ID":r["L3_ID"],"L1_ID":r["L1_ID"],"Disposition":"OUTPUT"})
    OUT.mkdir(parents=True,exist_ok=True)
    for d in DOMAINS:
        rr=[{k:v for k,v in r.items() if not k.startswith("_")} for r in final if L1_DOMAIN[r["L1_ID"]]==d]
        write(OUT/f"L4_{d}_Human_Review_Recovery_Applied.csv",rr,fields)
    write(OUT/"Source_Output_Lineage_Edges.csv",edges,["source_row_id","L4_ID","L3_ID","L1_ID","Disposition"])
    write(OUT/"Deletion_Tombstones.csv",tomb,["Register_ID","source_row_id","Deleted_L4_ID","Title_ko","Reason"])
    write(OUT/"Recovery_Application_Log.csv",decision_log,["Register_ID","Action","Status","Output_Keys"])
    regrows=read(REC/"Human_Review_Instruction_Register.csv"); bysrc=defaultdict(list)
    for e in edges: bysrc[e["source_row_id"]].append(e)
    ledger=[]
    for rr in regrows:
        src=rr["source_row_id"]; ee=bysrc[src]
        ledger.append({"Register_ID":rr["Register_ID"],"source_row_id":src,"Disposition":"DELETE" if src in deleted_sources else ("OUTPUT" if ee else "NO_BASELINE_OUTPUT"),"Output_L4_IDs":"|".join(e["L4_ID"] for e in ee),"Output_L3_IDs":"|".join(dict.fromkeys(e["L3_ID"] for e in ee)),"Output_Count":len(ee)})
    write(OUT/"Source_Disposition_Ledger.csv",ledger,["Register_ID","source_row_id","Disposition","Output_L4_IDs","Output_L3_IDs","Output_Count"])
    summary={"method":"HUMAN_REVIEW_LINEAGE_OVERLAY_NO_EM","input_cards":sum(len(read(BASE/f"L4_{d}_Human_Review_Round2_Applied.csv")) for d in DOMAINS),"output_cards":len(final),"output_by_domain":{d:sum(L1_DOMAIN[r["L1_ID"]]==d for r in final) for d in DOMAINS},"actions":dict(__import__('collections').Counter(x["Final_Action"] for x in decisions)),"others":0,"master_sha256":hashlib.sha256(MASTER.read_bytes()).hexdigest(),"decision_rows":len(decisions),"register_rows":len(regrows),"tombstones":len(tomb)}
    (OUT/"Recovery_Application_Summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
