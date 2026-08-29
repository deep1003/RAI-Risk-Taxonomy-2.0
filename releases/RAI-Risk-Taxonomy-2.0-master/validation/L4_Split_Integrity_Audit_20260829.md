# L4 Split Integrity Audit

Date: 2026-08-29

Status: audit and proposal only. No card was split, retired, or remapped in this audit.

## Scope and decision rule

The audit compared the current 778-card master with the 808-row human-review instruction register, the 166 approved recovery decisions, and final source-to-output lineage. A split is considered complete when materially different risk events, affected interests, causal mechanisms, or L3 scopes appear as separate outputs. A causal chain within one coherent risk mechanism is not split merely because its title or definition contains a conjunction.

## Human-review split fidelity

- Split-related instruction rows: 35
- Structurally and semantically realised: 33
- Explicitly overridden under source-evidence and immutable-L3 precedence: 2
- Lost split lineage: 0
- Exact bilingual duplicates among split outputs: 0

### Documented overrides

| Register ID | Source | Literal comment | Implemented outputs | Assessment |
|---|---|---|---|---|
| `HR2-0483` | `SRC-G-0442` | Value imposition, inconsistency, allocative discrimination, and representational harm | `G_INT_VALUE_010`; `G_SYS_INCONS_001` | The source concerns annotator preference bias and inconsistency but does not identify an allocation decision or representational harm. The two unsupported harms were not invented. The override is documented in both output rationales. |
| `HR2-0500` | `SRC-G-0246` | Democratic or civic-order erosion and illegal conduct | `G_INT_POL_001`; `G_SYS_MISINFO_020` | The source describes fabricated news, propaganda, social bots, and targeted influence. It does not establish illegality or a distinct societal-level democratic erosion outcome. The source-supported misinformation and political-manipulation mechanisms were separated instead. |

`HR2-0238` (`SRC-G-0027-S2`) and `HR2-0509` (`SRC-G-0027-S1`) each have one final output, but they are already the two derived branches of one earlier split. Together they preserve `G_SYS_MISINFO_012` personal misinformation and `G_SYS_SECADV_055` security threats from misuse and diffusion of dangerous or sensitive information. They are not an unimplemented single-output split.

## Additional high-priority split candidates

| Priority | Current card | Proposed decomposition | Reason |
|---:|---|---|---|
| 1 | `G_INT_SELF_003` 이용자의 정신·신체 건강을 위협하는 콘텐츠 | Self-harm/eating-disorder encouragement; panic or anxiety induction; misleading medical information and unsafe drug guidance | The card combines different behaviours, harms, and control objectives. Much of the self-harm and eating-disorder meaning is already represented elsewhere, so the umbrella should be retired after lineage is absorbed rather than duplicated. |
| 2 | `G_SYS_MISINFO_008` 데이터 오해석·유출에 의한 오결론과 민감정보 확산 | Erroneous medical or scientific conclusions; sensitive-data disclosure; generated-literature or knowledge-graph contamination | Misinterpretation, privacy breach, and epistemic-corpus contamination are independent failure mechanisms crossing misinformation, privacy, and societal epistemic harm. |
| 3 | `G_INT_COPY_005` 지식재산권 및 인격권 침해 | Copyright, trademark, or patent infringement; unauthorised commercial use of name, image, or likeness | Intellectual-property rights and personality or publicity rights protect different interests and require different remedies. Existing copyright cards can absorb the first branch. |
| 4 | `G_INT_PRIV_011` 산출물을 통한 개인·기업의 민감정보 노출 | Personal or inferred sensitive-data disclosure; enterprise confidential information and trade-secret disclosure | Personal privacy and organisational trade-secret exposure involve different rights holders, protected interests, and controls. |
| 5 | `G_SOC_DEMOC_002` 시민적·정치적 피해 | Personalised political manipulation; surveillance-based rights infringement; coercive or force-enabled disproportionate group harm | This is an umbrella card spanning political manipulation, privacy, violence or coercion, and discriminatory impact rather than one L4 mechanism. Existing specific cards should absorb supported branches before retirement. |
| 6 | `G_INT_WEAP_021` 사이버·과학 영역에서의 LLM 이중용도 역량 악용 | Cyber vulnerability discovery and exploitation; step-by-step assistance for dangerous scientific experiments | The two branches have different technical capabilities, threat actors, safeguards, and harm pathways even though both currently fall under Weapons and Armed Conflict. |
| 7 | `G_SYS_SECADV_048` AI 컴퓨팅 인프라의 자원 소진·보안 침해 | Distributed compute or energy resource-exhaustion attack; infrastructure compromise causing unauthorised access, manipulation, or disruption | Availability-oriented resource exhaustion and confidentiality or integrity compromise are distinct adversarial objectives and controls. |
| 8 | `G_SOC_CULT_021` 글쓰기 능력 저하와 학술 문헌 오염 | Individual writing-skill and expressive-capacity erosion; pollution of scholarly literature and academic-integrity degradation | The affected target and level of analysis differ: individual capability versus the collective knowledge ecosystem. |
| 9 | `G_INT_REL_001` AI 시스템에 대한 정서적·물질적·인식론적 의존 | Emotional or relational dependence; functional dependence in daily activity; epistemic overreliance in factual, moral, or strategic judgement | The card combines relationship harm, functional dependence, and miscalibrated epistemic reliance. The emotional branch overlaps an existing relationship-risk card and should be absorbed rather than duplicated. |
| 10 | `G_SYS_EVAL_012` AI 보증·감독 메커니즘의 실패 | Organisational assurance and audit-access failure; output accuracy and consistency failure; confidence-calibration failure; regulatory oversight failure | Board visibility, audit standards, output consistency, calibrated confidence, and regulatory supervision are separate governance and technical control failures spanning several L3 scopes. |

## Cards reviewed but recommended to remain unified

- `G_INT_WEAP_001`: development, acquisition, and deployment are lifecycle stages of the same weapon-capability risk.
- `G_INT_WEAP_011`: biological and chemical weapon or dual-use capability uplift remains one coherent mass-harm pathway.
- `G_SOC_ECON_009`: job displacement, deskilling, wage effects, and institutional instability form one labour-substitution causal chain.
- `G_SYS_TRANS_022`: explanation, verification, and defect diagnosis are connected consequences of the same black-box opacity mechanism.
- `G_SYS_SECADV_027`: robustness, resilience, and recovery under anomalous conditions are connected properties of one system-reliability mechanism.

## Recommended execution order

1. Correct no existing split solely on the basis of literal reviewer labels; the two overrides are justified by source evidence and the immutable L3 master.
2. Review the ten additional candidates against nearby existing L4 cards to distinguish new child creation from absorption into an existing representative.
3. Prefer absorption and retirement where a proposed child is already represented, preserving every `source_row_id` in the representative card.
4. Create a new child only when a materially distinct mechanism is not already covered.
5. Reissue L4 IDs, regenerate similarity artifacts from the new canonical CSVs, and validate lineage, domain counts, exact duplicates, and L3-master hash.

