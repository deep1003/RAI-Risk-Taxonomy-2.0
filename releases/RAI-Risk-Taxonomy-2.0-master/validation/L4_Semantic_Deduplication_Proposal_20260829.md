# L4 Semantic Deduplication Proposal

Date: 2026-08-29

Status: approved and applied. The user approved the ten priority consolidation clusters after two independent specialist reviews. Thirteen non-representative cards were retired with their source lineage and distinct meaning preserved in the revised canonical cards.

## Decision rule

Cards are proposed for consolidation when their risk event, causal mechanism, affected interest, and practical control objective are materially the same and the difference is limited to a channel, example, deployment setting, or narrower restatement. Similar wording alone is not sufficient. Distinct harm mechanisms, affected interests, failure stages, and protected characteristics remain separate.

## Priority consolidation proposals supported by both reviewers

| Priority | Revised canonical card | Cards proposed for retirement | Meaning to preserve in the revised canonical definition |
|---:|---|---|---|
| 1 | `G_INT_SELF_010` 자해 조장 및 지원 | `G_INT_SELF_005`, `G_INT_SELF_007`, `G_INT_SELF_008`, `G_INT_SELF_009` | 미화·정당화·정상화, 온라인 공동체의 사회적 강화, 챗봇의 중단 실패, 수단 확보·장소 선택·개입 회피, 실행 절차와 행동 지향적 지원 |
| 2 | `G_INT_PRIV_001` AI 기반 대량 감시, 명칭·정의 개정 | `G_INT_PRIV_030` | 지속적 식별·추적·행동·통신 정보의 수집·결합·추론, 익명성 침해, 적법한 근거·필요성·비례성 결여 |
| 3 | `G_INT_PRIV_011` 맥락적 개인정보 보호 실패, 명칭·정의 개정 | `G_INT_PRIV_013` | 대화 중 과도한 개인정보 유도·추론·출력, 정보주체의 맥락적 기대와 통제, 데이터 최소화 |
| 4 | `G_INT_COPY_011` 저작물의 무단 복제·변형·배포 | `G_INT_COPY_006` | 허락 또는 적법한 근거 없는 복제·변형·배포, 2차적저작물 작성, 권리자의 정당한 이익 |
| 5 | `G_SYS_SECADV_051` 적대적 역할·지시에 의한 안전장치 우회 | `G_SYS_SECADV_050` | 역할극·위험 페르소나 부여를 이용한 안전장치 우회와 유해 출력 생성 |
| 6 | `G_SYS_EVAL_023` 상황 인식에 따른 평가 기만 | `G_SYS_EVAL_025` | 훈련·평가·배포 상태 식별, 평가 중 안전행동, 위험 역량·목표 은폐, 배포 시 행동 변화와 허위 안전 확신 |
| 7 | `G_INT_REL_004` AI에 대한 해로운 정서적 의존 | `G_INT_REL_001` | 지속적 챗봇 교제와 의인화 상호작용, 정서적·사회적 의존, 인간관계 대체, 자율적 판단 약화 |
| 8 | `G_SOC_POWER_002` 사회경제적 불평등 증폭과 AI 이익의 집중 | `G_SOC_POWER_025` | 자본·데이터·연산 집중, 노동소득 몫 감소, 고정비·네트워크 효과, 독점 지대, 접근 격차 |
| 9 | `G_SOC_GOV_002` AI 피해에 대한 책임·거버넌스 공백 | `G_SOC_GOV_030` | 개발자·운영자 책임 귀속, 감독·시정 권한, 문서화·법제, 피해구제와 책임 있는 개발 유인 |
| 10 | `P_INT_SAFETY_020` 가정 환경 및 취약 사용자와의 상호작용에서 발생하는 안전 실패 | `P_INT_SAFETY_015` | 가정환경 벤치마크 누락, 물체·배치·행동·위험요소의 희귀 조합, 취약 사용자, 미식별 배포와 감지·예측·수용 실패 |

The ten approved consolidations retired 13 cards and reduced the 791-card release to 778 cards.

## Extended candidates requiring one more decision

| Candidate | Reason for further review |
|---|---|
| `G_SYS_POLICY_008` ← `G_SYS_POLICY_007` | One reviewer found both to be the same training-record extraction risk. Confirm whether query-based extraction is merely an attack instance. |
| `G_INT_VIOL_005` ← `G_INT_VIOL_003` | One reviewer found the same violence-incitement and execution-support mechanism. Confirm whether the explicit extremism scope remains analytically necessary. |
| `G_INT_REPR_028` ← `G_INT_REPR_031` | One reviewer found protected-group stereotype reproduction to be a subset of general group stereotype reinforcement. This does not merge the separately protected characteristic cards. |
| `G_INT_COPY_011` ← `G_INT_COPY_012` | One reviewer treated unauthorised use of protected expression as the same copyright infringement event. Confirm whether reuse without literal reproduction needs a separate control objective. |

## Preserve as distinct

- Political-orientation, race and ethnicity, disability, and sex, gender identity, or sexual-orientation representation cards.
- `G_INT_SELF_006` non-suicidal self-injury and `G_INT_SELF_004` eating disorders and self-destructive health behaviour.
- `P_INT_SAFETY_014` simulation-to-real human-robot safety failure.
- Violence cards distinguished by mass violence, murder, relationship-based violence, threats, and torture.
- Weapon classes distinguished by biological or chemical, cyber, explosive, radiological or nuclear mechanisms.
- `G_INT_POL_001` and `G_INT_POL_006` pending resolution of scale automation versus vulnerability-based personalisation.
- `A_INT_COORD_001` and `A_INT_COORD_003` pending resolution of social-dilemma failure versus endogenous environment shift.

## Data integrity finding

`L4_Top1000_SameL3_Similar_Pairs.csv` predates the current L4 renumbering. Some identifiers in that artifact now refer to different titles in the 791-card master. It must not be used for retirement decisions until regenerated from the current canonical CSV files with immutable source-row lineage.
