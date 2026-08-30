# RAI Risk Taxonomy 2.0 — Claude Code 인수인계서

작성 2026-08-30 · 인계 시점 HEAD `53ab073` (origin/main 동기) · 공개 사이트 <https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/>

---

## 0. 30초 요약

Codex가 만든 777장 릴리스를 **독립 검수(AC-01~AC-12)** 해서 현재 **629장**으로 정리했다. 모든 판단은 "리뷰어 에이전트 2인 독립 판정 → 합의(교집합)만 적용" 원칙으로 수행했고, 각 단계의 판정 원장이 리포지토리에 남아 있다. 데이터·웹·보고서·로컬 파일은 전부 동기화된 상태이며, **지금 당장 해야 할 필수 작업은 없다.** 남은 것은 사용자 결정 대기 중인 시정 후보들이다.

---

## 1. 현재 상태 (검증된 사실)

| 항목 | 값 |
|---|---|
| L4 카드 | **629장** (General 487 / Agentic 65 / Physical 77) |
| L3 | 46개 마스터 + Others 3(비어 있음) · **전 L3가 3장 이상 보유**, 빈 L3 0 |
| L3 마스터 SHA-256 | `e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df` (불변, 절대 변경 금지) |
| 매핑 | EM 334 / HD 295 (EM·Hybrid EM **재실행 금지**) |
| 레퍼런스 | 160장에 검증된 링크 부착 (25.4%) |
| 공개 CSV | **25컬럼** (L0~L4 계층·정의 한/영, facet, act-type) — 스코어·키워드·휴먼리뷰·References 제외 |
| 원천 계보 | 원천행 808건 전원 최종 상태 보유, 고아 0 (단 SRC-G-0125는 DELETE로 단절 — 아래 6절) |

### 파일 지도
- `releases/RAI-Risk-Taxonomy-2.0-master/data/` — 공개 25컬럼 CSV(사이트에서 다운로드되는 파일)
- `handover/RAI-Risk-Taxonomy-2.0-master_20260829/01_data/` — **전체 컬럼본**(References·휴먼리뷰·계보 포함). 데이터 수정은 여기를 진실 원본으로 삼고 공개 CSV를 파생 생성하는 방식이 안전하다.
- `public/data/releases/.../cards.json` — 웹 카드 데이터(629장, `references`·`human_reviews` 필드 포함)
- `projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_line_by_line_audit_claude/` — **검수 원장 일체**(54개 파일)
- `projects/.../08_full_csv_archive_20260829/` — 컬럼 축소 이전 전체 컬럼 원본 보관
- `releases/.../validation/Audit_Correction_Log.csv` — AC-01~AC-12 시정 이력(핸드오버 03_validation에도 동일본)
- `CLAUDE.md` — 작업 메모리(세션 간 컨텍스트). **새 세션은 이 파일을 먼저 읽을 것.**

---

## 2. 반드시 지켜야 할 하드 원칙

1. **자살 준비·실행 분리 유지.** SELF 계열은 준비(SELF_007)·실행(SELF_002)·조장(SELF_004)·위기 대응 실패(SELF_008) 4축으로 분리되어 있다. 어떤 통합에서도 준비 카드를 흡수하지 말 것. (AC-01은 이 원칙이 깨진 것을 되돌린 시정이다.)
2. **보호 속성 교차 통합 금지.** 정치 / 인종·민족 / 장애 / 성별·성정체성·성적 지향 등 REPR "X 기반 적대·차별적 표상" 열거군은 축이 다르면 절대 통합하지 않는다.
3. **VIOL 통합 정의에 자해·일반 불법행위 문구 불포함.**
4. **신규 L3 생성 금지, L3 마스터 46행 문자 불변**(해시 고정). Others 3개는 비운 채로 유지.
5. **EM / Hybrid EM 재실행 금지.** 기존 점수는 과거 근거로만 존재하며 공개 데이터에 노출하지 않는다.
6. **흡수·폐기된 L4 ID는 영구 결번**(재사용 금지, 재번호 금지).
7. **통합·분해 시 계보 합집합 보존**: `source_row_id`, `facet`, `act-type`.
8. **판단은 원장에 기록.** 데이터만 바꾸고 근거를 남기지 않으면 결함으로 본다(재생성 절차서 원칙).
9. **커밋·푸시는 사용자 승인 후.** 검수는 데이터 무변경이 기본.

---

## 3. 절차서 (작업 전 필독)

| 문서 | 용도 |
|---|---|
| `07_.../LINE_BY_LINE_AUDIT_PROCEDURE.md` | 검수 절차(Phase 0~5, 2b 의미중복 / 2c 복합카드 분해 / 2d 범위·측정성) |
| `07_.../REGENERATION_PROCEDURE.md` | **재생성 절차** — 원본 4개 CSV + 원장만으로 최종본을 결정론적으로 재현하는 파이프라인 |
| `06_.../SEMANTIC_MERGE_PROCEDURE.md` | 의미 기반 통합 절차 v2.0(ID가 아닌 명칭·정의로 카드 재식별) |
| `07_.../REFERENCE_ATTACHMENT_PLAN.md` | 레퍼런스 부착 절차(인용 조작 방지 설계 포함) |

**핵심 방법론**: 판단이 개입하는 모든 작업은 ① 리뷰어 에이전트 2인에게 **독립** 판정을 시키고(상호 산출물 열람 금지) ② 합의(교집합)만 적용하며 ③ 불일치는 제3자가 증거를 직접 확인해 총괄 판정한다. 단독 판정은 원장에 NOTE로 남기고 적용하지 않는다.

---

## 4. 지금까지의 시정 이력 (AC-01~AC-11)

| ID | 내용 | 카드 수 |
|---|---|---|
| AC-01 | 자살 준비 카드 복원 + 조장 카드 정의 축소 | 777→778 |
| AC-02 | 8개 대형 L3의 합의 중복 58장 흡수 | 778→720 |
| AC-03 | 휴먼 검토의견 원문·반영 결과를 237장에 기재, provenance 코드 문구 정리 | 720 |
| AC-04/04b | 공개 CSV를 27컬럼으로 축소(스코어·키워드 제거), 전체 컬럼 원본 보관 | 720 |
| AC-05 | 빈 L3 2곳 보충(과도한 거절 3장, 물리적 변조·파괴 3장, 전 카드 출처 링크) | 720→725 |
| AC-06 | 미달 L3 보강 2장(문헌 근거), GOV −10·UNETH −6 합의 흡수 | 725→711 |
| AC-07 | 전체 L3 MECE 큐레이션: 흡수 64, 귀속 이관 18, 제거 2 | 711→645 |
| AC-08 | 합의 복합 카드 18장 분해(17장 폐기, SELF_008 신설) | 645→629 |
| AC-09 | 기술보고서 KO/EN 전면 갱신·재컴파일, 전 파일 동기화, Mapping provenance 섹션 제거 | 629 |
| AC-10 | 공개 CSV에서 휴먼리뷰·References 컬럼 제거(25컬럼) | 629 |
| AC-11 | 160장에 검증된 레퍼런스 부착 | 629 |
| AC-12 | 릴리스 메타데이터 동기화: manifest 2벌 777→629 갱신, 렌더 실패하던 Release Manifest 페이지 복구, releases README 재작성, 툼스톤 2건 보완(19건), 빈 SHA256SUMS 재생성(23항목) | 629 |

---

## 5. 검증 결과 (완료된 감사)

- **휴먼검수 의도 반영 최종 검증(Fidelity-2)**: 의견 251건 전수 → **반영 238(94.8%) / 부분반영 11 / 미반영 2**. 보고서 `FIDELITY2_FINAL_REPORT.md`, 행별 원장 `Fidelity2_Adjudication.csv`.
- **레퍼런스 검증**: 고유 URL 131건 전수 재검증(arXiv 91/91, DOI 31/31, 기관 9/9), 주장 제목 대 실제 제목 158/158 일치, **인용 조작 0건**. 보고서 `REFERENCE_FINAL_REPORT.md`.
- **최종 릴리스 검수**: 기계 검사 전부 PASS(무결성·중복 0·계보 완전·L3 불변). 보고서 `AUDIT_FINAL_REPORT.md`.

---

## 6. 미결 사항 (사용자 결정 대기 — 임의로 진행하지 말 것)

### 6-1. Fidelity-2 권고 시정 5건 (`FIDELITY2_FINAL_REPORT.md` 6절)
1. **HR2-0778** — `P_SYS_CONTROL_036` 정의에 "열·전력 제한(쓰로틀링)" 기제 추가. AC-02 흡수 과정에서 소실된 유일한 즉시 복원 가능 항목.
2. **HR2-0675** — "Excessive Authority and Agency 이관" 미이행. AUTH 계열로 이관하거나 GOAL 잔류를 승인 결정으로 원장 등재.
3. **HR2-0340** — 이관 지시가 DELETE로 귀결(원천행 SRC-G-0125 계보 단절). 삭제 유지 여부 결정.
4. **HR2-0483 / HR2-0509** — 미분해 축(ALLOC·REPR / 명예훼손) 신설 또는 기존 카드 흡수 여부.
5. **HR2-0600~0602, 0700·0702·0704·0705** — 데이터 변경 없이 판단 근거만 원장에 등재하면 해소(검토 요청 결과, 상충 의견 중 유지를 택한 근거).

### 6-2. 미적용 잔여 판정
- **MECE 단독 플래그 50건** — `Reviewer_A_MECE.csv` / `Reviewer_B_MECE.csv`에서 한쪽만 플래그한 건. 재판정 지시 시 처리.
- **복합 카드 단독 검출 16건**(A 12 / B 4) — `Composite_Consensus.csv`.
- **범위·측정성 단독 41건** — `Scope_Quality_Flag_List.csv`.
- **레퍼런스 미부착 469장** — 사용자 지시로 공란 유지. 추가 부착을 원하면 `REFERENCE_ATTACHMENT_PLAN.md` 절차 재실행.

### 6-3. 방침 확인 사항
- **EVAL(65)·SECADV(45)·CONTROL(40)은 30장 초과 상태 유지.** 사용자 승인된 방침: 30장 강제 상한 없음, 합의된 중복만 제거. EVAL은 평가 실패 기제가 실제로 다양해 중복 제거만으로 30 이하가 불가능하며, 강제 통합은 측정성을 훼손한다.

---

## 7. 실무 함정 (반복해서 겪은 것들)

1. **CSV BOM**: 원본 릴리스 CSV는 UTF-8 **BOM 포함**이다. BOM 없이 저장하면 Excel이 한글을 CP949로 읽어 전부 깨진다. 파이썬으로 쓸 때 반드시 `encoding='utf-8-sig'`. (실제로 한 번 사고가 났고 커밋 `bb8cb3d`로 복구했다.)
2. **읽을 때도** `encoding='utf-8-sig'`로 열어야 첫 컬럼명에 `﻿`가 붙지 않는다.
3. **공개 CSV vs 전체 컬럼본**: 공개 CSV에는 `source_row_id`, `References` 등이 없다. 코드에서 `row['source_row_id']`를 무조건 참조하면 KeyError가 난다(실제 발생). 컬럼 존재 여부를 확인하고 쓸 것.
4. **동기화 대상이 많다**: 데이터 1건을 바꾸면 ①릴리스 CSV ②핸드오버 01_data ③cards.json 2벌(public + handover 04_web) ④manifest 4종 ⑤원장(Disposition·Lineage) ⑥index.html 2벌 수치 ⑦README ⑧SHA256SUMS ⑨핸드오버 zip 을 모두 갱신해야 한다. 누락하면 사이트 수치와 데이터가 어긋난다.
   AC-01~AC-11 동안 실제로 이 목록의 뒷부분이 누락됐다. `releases/.../manifest.json`과 `handover/03_validation/manifest.json`은 777장에 머물러 공개 Release Manifest 페이지에 잘못된 수치를 렌더했고, `releases/.../README.md`도 777장 기준이었으며, `SHA256SUMS.txt`는 AC-05 이후 0바이트였고, `Deletion_Tombstones.csv`에는 AC-07 제거 2건이 빠져 있었다. AC-12에서 전부 시정했다. **manifest를 고칠 때는 `assets/release-report.js`가 그 JSON을 렌더한다는 점을 같이 확인할 것** — 필드가 어긋나면 페이지가 통째로 실패한다.
5. **Claude Code에서는 git이 정상 동작한다.** 이전 세션(샌드박스)은 `.git` 잠금 파일 unlink가 막혀 `commit-tree` plumbing으로 커밋했고, push는 사용자 Mac에서 실행해야 했다. Claude Code는 로컬이므로 그냥 `git add/commit/push` 하면 된다. 만약 `.git/*.lock` 잔재로 막히면 `find .git -name '*.lock' -delete`.
6. **작업용 워크트리 `.audit_fix_wt/`가 리포 안에 남아 있다.** 불필요하면 `git worktree remove .audit_fix_wt --force`. 백업 브랜치 `codex-wip-backup-20260830`에는 Codex의 미커밋 작업분이 보존돼 있다.
7. **레퍼런스 링크 검증**: 일반 web fetch 도구는 arXiv/Crossref 같은 JSON·XML API에 빈 응답을 준다. Claude Code에서는 `curl`로 `http://export.arxiv.org/api/query?id_list=...` 와 `https://api.crossref.org/works/{DOI}` 를 직접 호출해 제목을 대조하면 된다. **"실재하는 DOI + 조작된 제목"이 LLM 인용의 지배적 실패 유형**이므로 반드시 제목 대조까지 할 것.
8. **matplotlib에 한글 폰트가 없는 환경이 있다.** 그림 라벨은 영문으로 두었다. 기술보고서 XeLaTeX는 `Noto Sans CJK KR`로 컴파일된다(Apple SD Gothic Neo는 해당 환경에 없었음).

---

## 8. 새 세션 시작 체크리스트

1. `CLAUDE.md`와 이 문서를 읽는다.
2. `git log --oneline -5`로 HEAD가 `53ab073` 이후인지 확인, `git status`가 깨끗한지 확인.
3. 데이터 상태 자가 검증(아래 스니펫)으로 629 / 46 L3 / 3장 이상 / References 160을 확인한다.
4. 작업이 데이터를 바꾸는 것이라면 관련 절차서를 먼저 읽고, 판단이 필요하면 리뷰어 2인 독립 판정 방식을 쓴다.
5. 변경 후에는 4절 동기화 9개 대상과 검증 게이트를 모두 통과시킨 뒤 사용자 승인을 받아 push한다.

```bash
python3 - <<'PY'
import csv, hashlib
from collections import Counter
H='handover/RAI-Risk-Taxonomy-2.0-master_20260829/01_data/'
cards=[]
for fn in ['L4_General.csv','L4_Agentic.csv','L4_Physical.csv']:
    cards+=list(csv.DictReader(open(H+fn, encoding='utf-8-sig')))
l3=Counter(c['L3_ID'] for c in cards)
print('cards', len(cards), Counter(c['L1_ID'] for c in cards))
print('L3', len(l3), 'min', min(l3.values()))
print('refs', sum(1 for c in cards if c.get('References','').strip()))
print('L3 sha', hashlib.sha256(open(H+'L1_L2_L3_Master.csv','rb').read()).hexdigest()[:8], '(expect e9439ced)')
print('dup titles', sum(1 for k,v in Counter(c['L4_Title_ko'] for c in cards).items() if v>1))
PY
```

---

## 9. 배포

GitHub Pages는 `main` 브랜치 루트에서 서빙된다. push 후 1~2분이면 반영되며, `index.html`의 `assets/site.js?v=...` 캐시 문자열을 갱신해야 브라우저가 새 스크립트를 받는다(현재 `v=master-20260830-ac11`). 배포 확인은 `https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/index.html?v=확인용` 을 열어 L4 수치를 보면 된다.
