# RAI Risk Taxonomy 2.0 master release

Current master: third-round human-review application (2026-09-01), following the second-round recovery and audit corrections AC-01 through AC-19.

- L3 master: 46 immutable source categories plus 3 derived Others queues
- L4: 623 cards
- General / Agentic / Physical: 494 / 66 / 63
- Retained mapping labels: EM 321 / HD 302
- Cards with a verified literature reference: 176
- Every substantive L3 remains populated; `P_SYS_HARDWARE` and `P_INT_TAMPER` each hold 2 cards after AC-19
- Final Others assignments: 0
- Deterministic AC-19 validation: 11 recorded checks, 11 PASS, 0 FAIL
- EM and Hybrid EM rerun in this review round: no
- L3 master SHA-256: `1ab58e1dd002d85de92db4bb1e49daa744d053a3950025bfe831bdef9bf98c54`

Prior-run mapping scores are retained only as historical evidence and are not published. The score and keyword columns were removed from the released CSVs by AC-04 and AC-10, so the published files carry 25 columns covering the L0 to L4 hierarchy, bilingual definitions, facet, and act-type.


## Round-3 human review

All 629 rows from the three KTSPACE review pages were read before transformation. The 30 non-empty comments produced 19 reassignments with definition revision, 6 deletions, and 5 same-L3 scope generalisations. Two independent expert reviewers assessed ambiguous cases, followed by third-party adjudication. No EM or Hybrid EM was run, and no merge, split, new L4, or new L3 was introduced. The final release contains 623 cards.

## AC-19 Physical AI minimum corrections

Two existing cards were reassigned across domains after two independent semantic audits and explicit user approval: `P_SYS_HARDWARE_001` became `G_SYS_PERF_017`, and `P_INT_TAMPER_001` became `G_SYS_SECADV_061`. The Korean definition of `P_SYS_HARDWARE_003` was corrected from `우주선(cosmic ray)` to `우주 방사선(cosmic ray)`. No card was deleted, merged, split, or newly created, and EM was not rerun. The 50-row L3 master remained byte-identical.

## Round-2 pipeline (historical)

The round-2 recovery produced 777 cards from 798 input cards through 166 approved row-level decisions: delete / merge / split 14 / 14 / 19, remap / rewrite-and-retain 80 / 39. Those stage figures are preserved under `round2_pipeline_historical` in `manifest.json`.

## Audit corrections

An independent line-by-line audit took the release from 777 to 629 cards. Every judgement was made by two reviewer agents working without sight of each other's output, and only the consensus was applied; disagreements went to a third-party adjudicator who checked the evidence directly. The full trajectory and the rationale for each step are in `validation/Audit_Correction_Log.csv`.

Canonical CSVs are under `data/`. The 808-row instruction register, approved decisions, lineage edges, deletion tombstones, application log, semantic-deduplication log, correction log, and validation record are under `validation/`.
