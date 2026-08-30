# Human Review Intent Audit

Date: 2026-08-30  
Mode: Read-only audit. No taxonomy, mapping, website, or release data were modified.

## 1. Scope

- Human-review source rows checked: 808 of 808
- Rows with a non-empty human-review comment: 251
- Rows with a non-empty source instruction prompt: 259
- Unique rows containing either form of instruction: 441
- Recovery decisions checked: 166 of 166
- Current source dispositions checked: 808 of 808
- Current final L4 cards checked: 777, comprising General 607, Agentic 77, and Physical 93
- Independent reviews: one lineage and data-integrity review, and one semantic and policy-ontology review
- Final adjudication: independent re-reading of the source instruction, current output, L3 master, decision ledger, deletion tombstone, and later user-approved transformation logs

## 2. Audit standard

The audit applied the following order of authority:

1. Immutable current L3 master
2. Explicit L4 instruction prompt and second-round human-review comment
3. Human-edited L4 wording
4. Original L4 content and immutable `source_row_id` lineage
5. Later explicit user-approved consolidation, split, deletion, or scope-curation decisions

A case is reported below only when the current disposition does not execute the explicit human-review action and the available decision record does not provide a case-specific, source-grounded explanation sufficient to demonstrate faithful implementation. A substantively defensible deletion can therefore still be an intent-compliance exception when a rewrite or remap instruction was silently converted into deletion.

## 3. Overall result

The release passes structural and lineage integrity checks. All 808 source rows have a terminal disposition, all 864 lineage edges resolve to existing final cards, deleted sources do not survive as final cards, and the L3 master is unchanged.

Three high-severity intent-compliance exceptions remain. They share the same failure pattern: the source requested `REWRITE` or `REMAP`, the agent proposals disagreed and required user approval, the comparison ledger retained `PENDING`, but a later recovery decision recorded `DELETE` without a case-specific human selection or an adequate explanation of why the original instruction could not be fulfilled.

## 4. Most serious exceptions

| Severity | Register and source | Verbatim human instruction | Current result | Final adjudication |
|---|---|---|---|---|
| Critical | `HR2-0232` / `SRC-G-0481` | `Title을 '동물 이익을 위한 AI 개발·배포 기회 상실'로 수정할 것. '이익이 되지 않 는'과 같이 한국어 띄어쓰기가 틀린 경우 '이익이 되지 않는'처럼 맞춤법을 준수할 것` | Deleted. No current L4 descendant. | The explicit title and spelling revision was not implemented. The two agent proposals were `REWRITE_KEEP → G_INT_VIOL` and `REMAP → G_INT_VALUE`; the approval ledger required user selection and remained `PENDING`. Deletion may be arguable under the later rule against topic or opportunity-only cards, but the tombstone contains only a generic cross-review statement and does not document that rationale. This is a critical traceable-intent failure, not a finding that the card must necessarily be restored. |
| Critical | `HR2-0230` / `SRC-G-0482` | Replace model or algorithm wording with `AI 시스템` and rewrite the ending as `사회경제적 안정과 국제 안보가 함께 흔들리는 리스크`. | Deleted. No current L4 descendant. | The requested wording revision was converted to deletion. The competing proposals were `SPLIT → G_SOC_ECON / G_SOC_DEMOC / G_INT_WEAP` and `DELETE`; the approval ledger required user selection and remained `PENDING`. The card is overbroad and deletion may be methodologically preferable, but the stored deletion rationale does not show that the explicit rewrite was considered and superseded under the later granularity rule. The implementation therefore fails intent traceability. |
| High | `HR2-0340` / `SRC-G-0125` | `(jay) [이관] Performance and Reliability Failure` | Deleted. No current L4 descendant. | The requested remap was not executed. The reviewer’s named category does not exist in the immutable current L3 master, and the source card mixes residual bugs, misaligned goals, weak capabilities, and command ambiguity. Deletion or decomposition can therefore be defended. However, the agent proposals were `DELETE` and `REMAP → G_SYS_EVAL`, the approval ledger required user selection and remained `PENDING`, and the tombstone does not explain why rewrite, decomposition, or the closest current L3 was rejected. This is a high-severity process and provenance exception. |

## 5. Rejected severe candidates

Two additional semantic-review candidates were not confirmed as severe violations after third-party adjudication.

- `HR2-0215 / SRC-G-0470`: the initially approved `G_SOC_DEMOC` umbrella was later retired and its political manipulation, surveillance, and disparate-impact meanings were absorbed into `G_INT_POL_006`, `G_INT_PRIV_001`, and `G_INT_ALLOC_008` under user-approved split record `SS-05`. This is a later authorised transformation, not an unrecorded loss.
- `HR2-0500 / SRC-G-0246`: the source-supported meanings were separated into `G_INT_POL_001` and `G_SYS_MISINFO_020`. The source does not independently establish illegality or a distinct societal-level democratic-erosion outcome. The departure from the reviewer’s provisional labels is explicitly explained in the split-integrity record and is not a severe violation.

## 6. Structural findings that are not violations

- Source disposition: 791 output sources and 17 deleted sources, mutually exclusive and collectively exhaustive
- Final lineage edges: 864, all resolving to current L4 cards
- Missing `source_row_id`: 0
- Deleted sources surviving in final outputs: 0
- Final cards without lineage: 0
- Others: 0
- Duplicate L4 IDs: 0
- Hierarchy mismatches: 0
- Final L4 counts: General 607, Agentic 77, Physical 93
- L3 master: unchanged

## 7. Conclusion

The current release is structurally coherent, but it is not fully compliant with the recorded human-review intent. The three cases above should be treated as decision-governance exceptions. No restoration, remapping, rewriting, or deletion reversal has been performed in this audit.
