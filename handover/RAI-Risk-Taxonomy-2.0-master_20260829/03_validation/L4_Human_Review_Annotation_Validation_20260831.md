# L4 Human-Review Annotation Validation

Date: 2026-08-31

## Scope

This validation treats each of the 629 current L4 cards as the unit of analysis. It checks whether the human-review comments displayed on a surviving card are attributable to its recorded source lineage and whether the displayed implementation result describes that card's current ID, L3 assignment, and disposition.

Source L4 cards retired through consolidation or deletion are not required to have their comments mapped to a surviving representative. No new L4 card was created.

## Method

1. Compare every displayed `human_reviews.comment` with the verbatim source comment in `Human_Review_Instruction_Register.csv` using `source_row_id`.
2. Confirm that the declared source row is present in the current card's immutable lineage.
3. Inspect every `human_reviews.result` for references to retired L4 IDs or pre-curation assignments.
4. Reword only stale or incomplete result annotations. Do not change the original comment, L4 title, definition, L1-L3 assignment, lineage, or card count.
5. Exclude comments belonging only to source cards retired through consolidation or deletion from the required-coverage denominator.

## Corrections

| Correction | Count |
|---|---:|
| Result annotations referring to retired or pre-curation L4 IDs | 31 |
| Results expanded to document the adjudication of conflicting keep/delete or domain suggestions | 4 |
| Original human-review comments changed | 0 |
| Human-review comments added from retired source cards | 0 |
| L4 cards created | 0 |
| L4 titles, definitions, mappings, or lineage records changed | 0 |

The four expanded adjudications concern `P_SYS_CONTROL_023`, `G_SYS_EVAL_044`, `P_SYS_CONTROL_042`, and `P_SYS_CONTROL_043`. Their result text now records why the current card was retained or reassigned after considering both parts of the original review comment.

## Validation result

| Check | Result |
|---|---:|
| Current L4 cards | 629 |
| Web human-review entries | 266 |
| Entries whose source comment differs from the original CSV | 0 |
| Entries whose declared source is absent from card lineage | 0 |
| Result annotations referencing a retired L4 ID | 0 |
| Empty result annotations | 0 |
| New L4 cards | 0 |

## Excluded retired sources

The following 12 source comments identified by the initial source-row coverage test belong to non-representative cards retired or absorbed during consolidation. In accordance with the approved scope, they were not added to current cards:

`SRC-G-0016`, `SRC-G-0096`, `SRC-G-0123`, `SRC-G-0227`, `SRC-G-0268`, `SRC-G-0317`, `SRC-G-0472`, `SRC-G-0484`, `SRC-P-0060`, `SRC-P-0104`, `SRC-P-0181`, and `SRC-P-0213`.

## Conclusion

PASS. Human-review comments currently displayed on surviving L4 cards match the original source comments, and their result annotations now describe the current cards without stale identifiers. The correction changed annotations only and created no L4 card.
