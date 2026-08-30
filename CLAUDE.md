# RAI-Risk-Taxonomy 작업 메모리

## 라운드2 라인바이라인 검수 (대기 중 — Codex 완료 시 실행)
- 절차서: `projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_line_by_line_audit_claude/LINE_BY_LINE_AUDIT_PROCEDURE.md` (v1.0)
- 개시 조건: Codex 완료 선언 + 자체검증 31/31 PASS + 2회 실행 해시 일치. FAIL 상태면 반려.
- 방식: 원천 808행 전수 대사(표본 아님). 판정 PASS/FAIL/QUERY/NOTE → `Audit_Ledger_L4.csv`. 검수 중 데이터 수정 금지, 이중 판정(에이전트 A 지시 이행 / B 언어·전거).
- 기준선: 커밋 6220567(798장: G630/A74/P94), KTSPACE 원본 4개 SHA 고정(manifest self-sha 171eff64979c), 휴먼 검토의견 251행.
- 판단 기준: 검토의견 원문 + `06_semantic_merge_plan_claude/SEMANTIC_MERGE_PROCEDURE.md` v2.0 + ID해석원장(통합 10건 기적용).
- 하드 원칙: 정치/인종·민족/장애/성별·성정체성·성적지향 교차 통합 금지, 자살 준비·실행 분리, VIOL 정의에 자해·불법행위 불포함, 신규 L3 금지, L3 마스터 46 문자 불변, EM 재실행 금지, 흡수 ID 재사용 금지, 계보(source_row_id/facet/act-type) 합집합 보존.
- 언어 규칙: 표준 띄어쓰기 vs 법전 표기(2차적저작물·정보주체 등) 구분, 1문장 명사형 종결("~하는 리스크."), 어휘 전거는 EU AI Act·AI기본법·개인정보 보호법·저작권법·NIST·KISDI·용어사전만.
- 완료 기준: FAIL 0 + QUERY 0 + Phase 0~5 PASS → AUDIT_FINAL_REPORT.md → 사용자 승인 후에만 배포(commit/push는 사용자 수동).
- 사용자 미결정 3건: WEAP_010 vs 014 통합 여부 / PRIV_020 vs 021 통합 여부 / WEAP_019 포괄 카드 유지 여부.

## 검수·재생성 쌍 문서 체계 (2026-08-29 확정)
- 검수 절차서와 쌍을 이루는 재생성 절차서: `projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_line_by_line_audit_claude/REGENERATION_PROCEDURE.md` (v1.0). 원칙: "판단은 원장(ledger)에 기록, 재생성은 원장 재생(replay)" — 새 세션에서 원본 4개 CSV + 원장 7종만으로 최종 산출물을 결정론적으로 재현(2회 실행 해시 일치)할 수 있어야 함.
- 의미 중복 통합 기준(검수 Phase 2b): `07_line_by_line_audit_claude/Semantic_Dedup_Merge_List.csv` — 리뷰어 에이전트 2인이 후보쌍 1,093건(1차 324+보충 769) 독립 판정. A_필수통합 14클러스터(예: SELF_009←006·008 채널 변형, VIOL_003←010, COPY_008←011, SECADV_009←005·033 역할·페르소나 우회, EVAL_024←026, GOV_029←032 등), B_단독플래그 21쌍(NOTE), C_사용자결정 32쌍. 전체 대사표: `Reviewer_Consensus_Matrix.csv`.
- 주의: 사이트/스냅샷 간 L4 ID 어긋남 존재(예: 화면의 SELF_007=커뮤니티, 릴리스 CSV의 SELF_006=커뮤니티) → 모든 대조는 명칭·정의 의미 매칭으로.
- 사용자 결정 대기(추가): SELF_009 vs 010(자살 실행 지원 흡수 여부 — 준비·실행 분리 원칙 경계), PRIV_019/020/021 노출 계열 정비, WEAP_019 포괄 카드, WEAP_010 vs 014, VALUE_020 vs 021, SECADV_004(일반 탈옥)·024(다중 벡터) 흡수 여부 등 32쌍.

## 다중의미 카드 분리 원칙 (사용자 확정 2026-08-29)
- 하나의 L4 카드가 다중 의미(이질적 리스크 축 병렬)를 가지면 분리한다. 단, 세부 카드가 이미 존재하는 의미 조각은 신규 카드 생성 대신 **기존 세부 카드에 의미와 source_row_id를 흡수한 뒤 포괄 카드를 폐기**(DECOMPOSE_ABSORB_RETIRE). 세부 카드가 없는 조각만 신규 분리(DECOMPOSE_NEW).
- 검수: LINE_BY_LINE_AUDIT_PROCEDURE.md Phase 2c (산출물 Audit_Composite_Cards.csv). 재생성: REGENERATION_PROCEDURE.md 4b단계 + Composite_Resolution_Ledger.csv(분해 원장).
- 기지 복합 카드 후보(우선 검수): SELF_002, COPY_009, WEAP_002, WEAP_028, WEAP_019, ANTH_009, MISINFO_004, VIOL_005, UNETH_004. 최종 결정은 사용자 승인 후 원장 등재.

## 범위·측정성 결함 스캔 (2026-08-29)
- 기준 파일: `07_line_by_line_audit_claude/Scope_Quality_Flag_List.csv` — 리뷰어 2인 독립 전수 스캔(798장) 대사표. 합의 98건(BROAD 76/VAGUE 18/유형상이 3/NARROW 1: VALUE_020), 단독 41건(NOTE). 검수 절차서 Phase 2d 등재.
- 최다 결함 군집: G_Others 28건(메가 우산 카드 집적지, 예: G_Others_078), G_INT_WEAP 7~9건(WEAP_005·010·018·019·021 역량 우산 군집). L3 재진술형 우산 카드가 L3마다 1~2장 반복(ALLOC_008, MISINFO_013, GOV_032 등).
- 조치 체계: BROAD→DECOMPOSE(Phase 2c 원칙)/SHARPEN, VAGUE→SHARPEN, NARROW→ABSORB/GENERALIZE. 처리 방침은 사용자 승인 후 원장 등재. 통합 대표이면서 BROAD인 카드(SELF_009, REL_006, ECON_008)는 통합 후 SHARPEN.

## 최종 릴리스 검수 결과 (2026-08-29, 조건부 반려)
- 대상: 핸드오버 fb40929(=origin/main, 릴리스 8a948f8), 777장(G607/A77/P93). 보고서: `07_line_by_line_audit_claude/AUDIT_FINAL_REPORT.md`, 판정 원장: `Final_Audit_Consensus.csv`.
- 기계 검사 전부 PASS(SHA·L3 불변 e9439ced·중복 0·계보 808 완전·EM 미노출·REPR 분리·VIOL 클린).
- **FAIL 1건(리뷰어 2인 합의)**: 자살 준비·실행 분리 파괴 — 준비 카드 소멸, 준비 내용이 G_INT_SELF_004(조장)에 흡수, SELF_002·001과 재중복, rationale 자기모순. 수정안은 커밋 61d2e89(브랜치 audit-fix-ac01)로 직접 적용 완료(준비 카드 G_INT_SELF_007 복원 + SELF_004 정의 축소, 777→778, 시정 후 검증 24항목 ALL PASS). push는 사용자 수동.
- NOTE 9건: 내 A_필수통합 14클러스터 중 9건 미적용(Codex는 자체 USER_APPROVED 통합 세트 SD-01~10 적용). 재지시 시 일괄 통합.
- 주의: 릴리스 작업 트리는 별도 워크트리(RAI-Risk-Taxonomy-human-review-recovery-20260829, 마운트 밖). 검수는 git 객체 추출로 수행.

## AC-01 시정 적용 (2026-08-29, 커밋 61d2e89 / 브랜치 audit-fix-ac01)
- FAIL-F1 시정: G_INT_SELF_007 "자살 준비 행위의 조장 및 구체적 지원" 복원(기준선 문안, 계보 SRC-G-0512·0507 재귀속), G_INT_SELF_004 정의 축소(수단 확보·장소 선택·개입 회피·실행 절차·은폐 전략 문구 제거). 24개 파일 동기화: 릴리스 CSV·핸드오버 01_data·cards.json 2종·manifest 4종·원장(Disposition/Lineage)·Audit_Correction_Log.csv 신설·index.html 2종·README·SHA256SUMS(23항목)·zip 재생성. 시정 후 검증 24항목 ALL PASS.
- 미해결: 사용자 push 필요(git push origin audit-fix-ac01 후 main 병합). 샌드박스 git은 unlink 불가로 plumbing(commit-tree) 사용, 워크트리 .audit_fix_wt 잔존(수동 정리 필요 시 git worktree remove).

## 8개 L3 중복성 검수 (2026-08-29, 시정 릴리스 778장 기준)
- 파일: `07_line_by_line_audit_claude/L3_Redundancy_Consensus.csv`(판정), `Reviewer_A/B_L3_Redundancy.csv`(클러스터 원장), `L3_Redundancy_Input_Cards.csv`(331장 입력).
- 리뷰어 2인 독립 판정: A 79장/B 87장 삭제 가능, **합의(교집합) 58장** — EVAL 7/SECADV 14/CONTROL 14/REPR 4/WEAP 7/PRIV 4/VALUE 7/MISINFO 1. 합집합 108장(단독 50장은 검토 필요).
- **AC-02로 적용 완료(커밋 9c9de79)**: 778→720장(G564/A77/P79, EM391/HD329). 흡수 원장 `AC02_Absorption_Ledger.csv`(대표 충돌 19건 총괄 판정 포함), ID 재번호 없음(영구 결번). 검증 12게이트 ALL PASS. push 사용자 수동.
- 하드 가드 유지: REPR 보호 속성 열거군 통합 0건, 기술 축(백도어/미세조정/인코딩 등)·무기 유형 축·평가 메커니즘 축은 보존.

## 휴먼검토의견 반영 검토 (완료, 2026-08-29 → AC-03 커밋 9144759)
- 720장 기준 재검토 완료. 에이전트 2인 전수 판정+총괄: **반영 246 / 부분반영 3(HR2-0483 4축 중 2축, HR2-0509 명예훼손 축 미처리, HR2-0778 열·전력 기제 소실) / 미반영 2(HR2-0340 이관→삭제 계보 단절, HR2-0675 AUTH 이관 미이행)**. 보고서: `HUMAN_COMMENT_FIDELITY_REPORT.md`(원인 분석·NOTE 19건·권고 시정 4건 포함), 원장: Fidelity_Reviewer_A/B.csv, Fidelity_Consensus_Issues.csv.
- AC-03 적용 완료: 237개 카드에 휴먼 리뷰 원문+반영 결과 기재(cards.json human_reviews 필드 290건, CSV 신규 컬럼 Human_Review_Comment/Result). Mapping provenance를 코드 나열→한국어 라벨로 정리(hd_reason 코드값 삭제, 한국어 근거문만 유지), site.js 렌더링에 "휴먼 리뷰/반영 결과" 블록 추가(cache v=ac03). 검증 PASS. 미반영·부분반영 5건의 시정은 사용자 결정 대기(보고서 5절 AC-04 후보). push 사용자 수동.

## AC-04~05 및 재조정 제안 (2026-08-29 최신 상태)
- 배포 HEAD: 8052823 (main=audit-fix-ac01). 725장(G566/A77/P82, EM391/HD334). AC-04/04b: 공개 CSV 27→28컬럼(References 추가, 스코어·키워드 제거, 전체 컬럼 원본은 projects/08_full_csv_archive_20260829 + 핸드오버 01_data). AC-05: 빈 L3 보충(G_SYS_OREF 3장, P_INT_TAMPER 3장 — GOAL_022 분리·SECADV_054 이관·신규 4장, 전 카드 검증된 References 링크: XSTest/OR-Bench/AgentHarm/Cao CCS2019/NIST 800-82r3/800-193). site.js에 References 섹션(cache ac05). 신규 카드 5장은 원천행 계보 없음(AUDIT_NEW, 검수 게이트 예외 명시).
- push 방법 확립: osascript로 사용자 Mac에서 git push (샌드박스는 자격증명 없음). main으로 ff push: git push origin audit-fix-ac01:main.
- 재조정 제안서: `07_line_by_line_audit_claude/L3_REBALANCE_PROPOSAL.md` — ①미달 2곳(G_SYS_INCONS·A_SYS_SELFCOR 각+1, 문헌 검증: Sclar ICLR2024 2310.11324, Huang ICLR2024 2310.01798) ②30장 초과 5곳: GOV −10·UNETH −6 합의 즉시 감축(Reviewer_A/B_GOV_UNETH.csv), EVAL/SECADV/CONTROL은 단독 플래그 재판정으로 −9~15 추가 여지, EVAL은 30 이하 불가(기제 다양성) 명시. 승인 대기.

## AC-06~07 적용 완료 (2026-08-29 최종 상태)
- 배포 HEAD: b1f22bd (main 동기). **645장(G503/A65/P77, EM349/HD296), 46개 L3 전부 3장 이상, 빈 L3 0.**
- AC-06(2b0d386): 미달 L3 보강 2장(INCONS_003 Sclar ICLR2024 / SELFCOR_003 Huang ICLR2024, References 기재) + GOV −10·UNETH −6 합의 흡수. 725→711.
- AC-07(b1f22bd): 전체 L3 MECE 큐레이션(리뷰어 2인 전수 판정 Reviewer_A/B_MECE.csv, 합의만 적용) — 흡수 64(대표 충돌 9건 총괄 판정), 귀속력 이관 18(새 ID, 구 ID 결번: 예 작업장 감시 로봇→PRIV, 로봇 침입·절도→ILLEGAL, 플래시 크래시→CASCADE), 제거 2(원천행 DELETE·툼스톤 SRC-G-0352·0489). 711→645. 검증 13게이트 ALL PASS.
- 미적용 잔여: MECE 단독/불일치 플래그 50건 + ABSORB·TRANSFER 충돌 미합의분(원장에 기록) — 재판정 지시 시 처리. EVAL(65)·SECADV(45)는 기제 다양성으로 30 초과 유지(사용자 승인된 방침: 강제 30 상한 없음, 합의 제거만).

## 통합 후 복합 카드 검출 (2026-08-29, 645장 기준 — 적용 대기)
- 파일: `07_line_by_line_audit_claude/Composite_Consensus.csv` (판정 원장: Reviewer_A/B_Composite.csv, 입력: Composite_Scan_Input.csv 통합대표 138장 표기).
- 합의 COMPOSITE 18장 (통합대표 7 포함): SECADV 5(032 탈옥 3기전, 035 도구/표적, 037 절취/변조, 039, 040), WEAP 3(001, 005, 028), SELF_004(작위/부작위 — 조장 축 SHARPEN + 위기 대응 실패 NEW, 준비·실행 분리 비저촉), SEX_006, ANTH_009, UNETH_001, VALUE_026, CULT_003, GOV_001, POWER_013, MISINFO_014, TRANS_011.
- 해소 방향 합의: 대부분 DECOMPOSE_ABSORB_RETIRE(조각 전부 기존 세부 카드 귀속 후 폐기), NEW는 SELF_004 부작위 축 1건 정도. 대표 대상 소이(小異)는 총괄 조정 필요. A단독 12/B단독 4는 검토 대기.
- **AC-08로 적용 완료(커밋 517a0c2, 배포됨)**: 17장 분해·폐기(조각 전량 기존 카드 귀속, 계보·act-type 합집합 분배), SELF_004 조장 축 SHARPEN(명칭 "자해·자살의 미화·조장·정상화"), G_INT_SELF_008 "자해·자살 위기 신호에 대한 대응·개입 실패" 신설(References: Moore et al. FAccT 2025 arXiv:2504.18412, 원문 인용 "respond inappropriately to certain common (and critical) conditions"). 645→629장(G487/A65/P77, EM334/HD295). SELF 8장: 준비(007)·실행(002)·조장(004)·부작위(008) 분리. 검증 12게이트 PASS. 단독 16장(A12/B4)은 미적용 잔여.

## AC-09 전체 동기화 (2026-08-30, 커밋 f8c9570 — 배포 확인 완료)
- 기술보고서 KO/EN 629장 기준 전면 재작성·XeLaTeX 재컴파일(폰트 Noto Sans CJK KR로 교체 — 샌드박스에 Apple SD Gothic 없음). 감사 시정 AC-01~08 요약표 + 궤적 그림(audit_corrections_trajectory.png) 추가, 도메인 그림 갱신(그림 라벨은 영문 — matplotlib CJK 불가). 보고서 사본 4벌+핸드오버 02_reports+프로젝트 내부(technical_report, output/pdf) 동기화.
- 내부 스냅숏 동기화: 03_outputs/release, 07_human_review_recovery_applied → 최종 629장.
- **카드 상세에서 Mapping provenance 섹션 제거(사용자 지시)** — 휴먼 리뷰(검토의견/반영 결과)와 References는 독립 섹션으로 유지. site.js cache v=ac09.
- 라이브 확인: 629 L4 · G487/A65/P77 · EM334/HD295, 신규 보고서 PDF 배포됨.
- 유의: 사용자 로컬 main 체크아웃(마운트 폴더)은 6220567에 머물러 있고 Codex의 미커밋 수정과 충돌 위험이 있어 ff 병합을 시도하지 않음. 로컬 갱신 원하면 사용자가 stash 후 git pull.

## Fidelity-2: 휴먼검수 의도 반영 최종 검증 (2026-08-30, 629장 기준 — 검증 전용, 데이터 무변경)
- 계획서 `FIDELITY2_PLAN.md`, 결과서 `FIDELITY2_FINAL_REPORT.md`, 원장 4종(Fidelity2_Input/Reviewer_A/Reviewer_B/Adjudication).
- 방법: 의견 251건 전수 추적(원천행→등록부→처분원장→최종 문안). 검수 에이전트 2인 독립 판정 + 제3자 총괄 라인바이라인 재검토. 원문 일치 251/251, 귀착 카드 결손 0.
- **최종: 반영 238(94.8%) / 부분반영 11 / 미반영 2.** 검수자 일치 248/251, 불일치 3건(CASCADE 병합 검토 요청)은 총괄이 B의 PARTIAL 채택.
- 미반영 2건(1차와 동일): HR2-0340(이관→DELETE, 유일한 계보 단절), HR2-0675(AUTH 이관 미이행, 통합이 이관을 덮어씀).
- 부분반영 11건: 분해 범위 미달 2(0483·0509), **AC 변형 중 새 소실 2**(0778 열·전력 기제 AC-02 소실 / 0710 명명 요청 AC-07 미반영), 검토요청 미기록 3(0600~0602), jw 상충 의견 일방 채택 4(0700·0702·0704·0705).
- 1차(720장) 대비: 246/3/2 → 238/11/2. 증가분 8 = 새 실질 소실 2 + 판정 엄격화 6(근거 미기록을 부분반영으로 하향).
- 권고 시정 5건(보고서 6절): ①CONTROL_036에 열·전력 기제 문구 추가 ②HR2-0675 AUTH 이관 또는 승인 등재 ③HR2-0340 삭제 유지 결정 ④0483·0509 미분해 축 결정 ⑤7건은 데이터 변경 없이 판단 근거 원장 등재. 전부 사용자 결정 대기.
