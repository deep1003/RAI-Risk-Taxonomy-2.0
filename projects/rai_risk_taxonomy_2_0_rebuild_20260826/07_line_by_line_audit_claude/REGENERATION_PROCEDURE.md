# RAI 2.0 라운드2 재생성 절차서 (Regeneration Procedure) — v1.0

작성 2026-08-29 · 작성자 Claude
목적: **별도 세션에서, 원본 4개 CSV와 결정 원장만으로 최종 산출물을 결정론적으로 재생성**할 수 있도록 생성 파이프라인 전체를 문서화한다. 본 문서는 `LINE_BY_LINE_AUDIT_PROCEDURE.md`(검수 절차서)와 쌍을 이루며, 검수는 "이 절차대로 생성되었는가"를 확인하는 행위다.

## 핵심 설계 원칙 — 판단의 원장화, 재생성의 재생(replay)화

모든 **판단적 결정**(휴먼 의견 해석, 통합/삭제/이관, 문안 확정)은 사람·에이전트가 내리되 반드시 **원장(ledger) CSV에 기록**하고, **재생성은 원장을 기계적으로 재생(replay)** 하는 것으로 정의한다. 따라서 재생성 시 어떤 재판단도 일어나지 않으며, 동일 입력 + 동일 원장 → 동일 출력(해시 일치)이 보장되어야 한다. 판단 없이 재현이 안 되는 단계가 발견되면 그 단계는 원장화가 누락된 것으로 보고 결함으로 처리한다.

## 1. 고정 입력 (변경 금지)

| 입력 | 위치 | 무결성 |
|---|---|---|
| 기준 마스터 (798장: G630/A74/P94, L3 49) | git 커밋 `6220567` 의 `releases/RAI-Risk-Taxonomy-2.0-master/data/` | 커밋 해시 |
| KTSPACE 라운드2 검수 원본 4개 (L3 46행 + L4 808행, 검토의견 251행) | `00_source_snapshot/csv/` | `source_manifest_human_review_round2_20260828.json` SHA-256 4건, manifest self-sha `171eff64979c` |
| L3 마스터 46 | 기준 커밋 내 | 필드 해시 고정, 문자 불변 |

## 2. 결정 원장 (재생성의 유일한 판단 소스)

| 원장 | 내용 |
|---|---|
| `05_human_review_round2/Human_Review_Round2_Decision_Ledger.csv` | 원천 808행 × 결정(KEEP/EDIT/SPLIT/MERGE/TRANSFER/DELETE 계열) + 근거. `L4_ID_Before` 로 통합 이전 ID 보존 |
| `05_human_review_round2/user_directed_operations.csv` | 사용자 직접 지시(통합 10건 등)의 지시ID→당시ID→대표ID 해석 기록 |
| `06_semantic_merge_plan_claude/Semantic_Merge_ID_Resolution.csv` | 지시 10건의 의미 기반 재식별 원장 |
| `07_line_by_line_audit_claude/Semantic_Dedup_Merge_List.csv` | 의미 중복 통합 리스트 (A_필수통합 14클러스터 + 사용자 결정 반영분) |
| `07_line_by_line_audit_claude/Reviewer_Consensus_Matrix.csv` | 리뷰어 2인 판정 전체 대사표 (A합의/B단독/C사용자결정) |
| 분해 원장 (`Composite_Resolution_Ledger.csv`) | 다중의미 카드의 의미 조각→귀속 카드 매핑, `source_row_id` 분배 기록, 포괄 카드 폐기 기록 |
| 한국어 교정 원장 (`Korean_Copyedit_*.csv`) | 교정 전후 문안 대조. 승인 문안 잠금 목록 포함 |
| L3 원장 (`L3_Human_Review_Round2_Decision_Ledger.csv`) | L3 46행 결정(구조 불변 확인) |

## 3. 재생성 파이프라인 (순서 고정, 각 단계 결정론적)

1. **환경 준비**: 깨끗한 작업본에서 기준 커밋 `6220567` 체크아웃. 원본 4개 CSV SHA-256 == manifest 검증. 불일치 시 즉시 중단.
2. **휴먼 검토의견 적용**: Decision Ledger를 원천행 순서대로 재생. 의견 해석은 재수행하지 않고 원장의 결정·산출 문안을 그대로 적용. (KEEP: 무변경 / EDIT: 원장의 확정 문안 / SPLIT: 원장에 기록된 분리 카드들 / MERGE: 대표 카드 문안 + 계보 합집합 / TRANSFER: 지정 L3 / DELETE: 제거 + 사유)
3. **사용자 직접 지시 통합**: `user_directed_operations.csv` + ID해석원장 재생 (10건, 권고 문안 문자 그대로).
4. **의미 중복 통합**: `Semantic_Dedup_Merge_List.csv`의 A_필수통합 클러스터와 사용자 결정이 내려진 C등급 건을 재생. 대표 카드 문안·계보 합집합(`source_row_id`/`facet`/`act-type`) 보존, 흡수 ID 제거.
4b. **다중의미 카드 분리·흡수**: 분해 원장(`Composite_Resolution_Ledger.csv`) 재생. 원칙 — 하나의 L4가 다중 의미를 가지면 분리하되, **세부 카드가 이미 존재하는 의미 조각은 신규 카드를 만들지 않고 기존 세부 카드에 의미·`source_row_id`(facet/act-type 포함)를 흡수한 뒤 포괄 카드를 폐기(DECOMPOSE_ABSORB_RETIRE)**. 세부 카드가 없는 조각만 신규 분리 카드(DECOMPOSE_NEW) 생성. 의미 조각 유실 0, 폐기 ID 재사용 금지.
5. **Others 폐쇄**: 원장에 기록된 재배정 결정 재생 (신규 L3 생성 금지).
6. **한국어 교정 패스**: 교정 원장 재생 (잠금 문안 변경 0).
7. **ID 재번호(compaction)**: L3별 연속 번호 규칙(`id_continuity_per_l3`)을 결정론적으로 적용. 정렬 키 고정(도메인→L3→기존 순번). 흡수·삭제 ID 재사용 금지.
8. **산출물 생성**: 릴리스 CSV 5종, 웹 데이터(site.js), 기술보고서 수치, manifest/validation 페이지.
9. **검증 게이트**: 자체검증 31항목 전부 PASS (Others 0, 정확 중복 0, 계보 완전, 원천 808행 전원 최종 상태, L3 해시 일치, 한영 필드 완전, 승인 문안 비의도 변경 0, 분리 유지 원칙 위반 0 등).
10. **재현성 증명**: 1~9를 깨끗한 환경에서 2회 실행, 산출물 SHA-256 완전 일치 확인. 일치 실패 시 비결정 단계를 색출해 원장화.

## 4. 재생성 세션 개시 체크리스트 (새 세션용)

- [ ] 본 문서와 검수 절차서, CLAUDE.md 메모리 읽기
- [ ] 기준 커밋·원본 SHA 검증 (1단계)
- [ ] 원장 7종 존재·스키마 확인 (2절 표)
- [ ] 파이프라인 1→10 순차 실행, 단계별 중간 산출물 해시 기록
- [ ] 게이트 FAIL 시: 데이터 수정 금지, FAIL 원인을 원장 결함/재생 구현 결함으로 분류해 보고 후 중단
- [ ] 완료 후 검수 절차서(Phase 0~5) 기준으로 자체 검수

## 5. 금지 사항 (생성·재생성 공통)

EM/Hybrid EM 재실행 금지 · 신규 L3 생성 금지 · L3 마스터 46 문자 변경 금지 · 원본 4개 CSV 수정 금지 · 원장 없는 임의 판단 금지 · 흡수 ID 재사용 금지 · 정치/인종·민족/장애/성별·성정체성·성적지향 교차 통합 금지 · 자살 준비·실행 통합 금지 · VIOL 통합 정의에 자해·일반 불법행위 포함 금지 · commit/push는 사용자 수동.
