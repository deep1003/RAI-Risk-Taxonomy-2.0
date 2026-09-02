# RAI Risk Taxonomy 2.0 master release

Current master: fourth-round human-review application and L3 reference synchronisation (2026-09-03), following audit corrections AC-01 through AC-20.

- L3 master: 47 formal categories; no derived Others rows
- L4: 622 cards
- General / Agentic / Physical: 492 / 67 / 63
- Retained mapping labels: EM 309 / HD 313
- Cards with a verified literature reference: 622
- Every substantive L3 remains populated; `P_SYS_HARDWARE` and `P_INT_TAMPER` each hold 2 cards after AC-19
- Final Others assignments: 0
- Deterministic current-release validation: 16 recorded checks, 16 PASS, 0 FAIL
- EM and Hybrid EM rerun in this review round: no
- L3 master SHA-256: `24d1e3bb3485cc29bc9604f516310c07358f58eee340054e5eea0d62d2410efa`

Prior-run mapping scores are retained only as historical evidence and are not published. The score and keyword columns were removed from the released CSVs by AC-04 and AC-10, so the published files carry 25 columns covering the L0 to L4 hierarchy, bilingual definitions, facet, and act-type.


## Round-3 human review

All 629 rows from the three KTSPACE review pages were read before transformation. The 30 non-empty comments produced 19 reassignments with definition revision, 6 deletions, and 5 same-L3 scope generalisations. Two independent expert reviewers assessed ambiguous cases, followed by third-party adjudication. No EM or Hybrid EM was run, and no merge, split, new L4, or new L3 was introduced. The final release contains 623 cards.

## AC-19 Physical AI minimum corrections

Two existing cards were reassigned across domains after two independent semantic audits and explicit user approval: `P_SYS_HARDWARE_001` became `G_SYS_PERF_017`, and `P_INT_TAMPER_001` became `G_SYS_SECADV_061`. The Korean definition of `P_SYS_HARDWARE_003` was corrected from `우주선(cosmic ray)` to `우주 방사선(cosmic ray)`. No card was deleted, merged, split, or newly created, and EM was not rerun. This paragraph records the historical AC-19 state; the current 47-row L3 master is identified above.

## Round-2 pipeline (historical)

The round-2 recovery produced 777 cards from 798 input cards through 166 approved row-level decisions: delete / merge / split 14 / 14 / 19, remap / rewrite-and-retain 80 / 39. Those stage figures are preserved under `round2_pipeline_historical` in `manifest.json`.

## Audit corrections

An independent line-by-line audit took the release from 777 to 629 cards. Every judgement was made by two reviewer agents working without sight of each other's output, and only the consensus was applied; disagreements went to a third-party adjudicator who checked the evidence directly. The full trajectory and the rationale for each step are in `validation/Audit_Correction_Log.csv`.

Canonical CSVs are under `data/`. The 808-row instruction register, approved decisions, lineage edges, deletion tombstones, application log, semantic-deduplication log, correction log, and validation record are under `validation/`.
