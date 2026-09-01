# Third-Round Human Review Application Method

## Scope

All 629 rows in the three KTSPACE third-round review tables were read before any transformation. Thirty rows contained reviewer comments and 599 rows contained no requested change.

## Procedure

1. Freeze the three source CSV files and match every L4 ID to the current master.
2. Interpret each non-empty comment against the current L4 meaning and the unchanged 50-row L3 master.
3. Obtain two independent expert judgements for ambiguous or conflicting cases.
4. Adjudicate disagreements without EM, Hybrid EM, keyword voting, or nearest-category forcing.
5. Apply only the requested or necessary semantic operation: 19 reassignments, 6 deletions, and 5 scope generalisations.
6. Preserve old-to-new ID lineage and deletion tombstones. No merge, split, new L4, or new L3 is introduced.
7. Verify card counts, unique IDs, zero Others assignments, exact comment preservation, and byte-identical L3 master content.

## Adjudicated cases

- `G_INT_SELF_006`: moved to `G_SYS_CONTEXT`, preserving the contextually inappropriate-content mechanism without adding unsupported manipulative intent.
- `P_INT_SAFETY_007`: retained as a distinct card after removing the household limitation because the third-round comment did not authorise a merge.
- `P_INT_SAFETY_004`: moved to `G_INT_UNETH` because both expert reviewers found a direct conflict with the Physical Safety L3.
