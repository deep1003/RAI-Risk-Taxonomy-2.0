# v1.0.0 mapping methodology

1. Freeze and hash the global 1,726-card source, Physical AI 182-card source, and user-provided 50-L3 definitions.
2. Allocate `RAI4-####` by ASCII lexicographic order of frozen global source IDs.
3. Apply the 182-card Physical lock before any model call. Resolve 13 non-identical IDs only through the fixed alias table.
4. For each remaining card, build a hierarchy-blind input from its label, the direct mechanism sentence of its definition, and evidence title. Remove the templated sentence that restates the legacy hierarchy.
5. Rank all 26 non-Physical L3 definitions with normalized BGE-M3 embeddings at explicitly pinned revision `5617a9f61b028005a4858fdac845db406aefb181` and strict positive-cue, exclusion, and gap-sentinel rules.
6. Run two independent local small-model reviews over a broader plausible pool as a hierarchy-blind sensitivity audit. Each model sees the full 26-L3 codebook but not the BGE ranking, the other model's result, or the legacy hierarchy. These outputs are not approval authority.
7. Send all strict BGE/rule proposals to two independent frontier expert reviewers in a hierarchy-blind packet. Create `algorithm_proposed` only when both reviewers approve the exact proposed L3. A rejection or split decision becomes `needs_taxonomy_decision`.
8. Keep every other card as `needs_taxonomy_decision` without a primary L3.
9. Perform post-hoc legacy transition and unresolved-cluster analyses only after placements are frozen.
10. Run schema, cardinality, referential-integrity, source-hash, Physical-lock, two-expert-consensus, and site-bundle validation.

The revision pin was independently rerun after an audit found that an earlier run recorded the wrong cached snapshot name. The pinned rerun produced byte-identical algorithm scores and the same 61-card expert-review packet, so the two completed expert reviews remained valid. The reproducibility record is stored in `reports/validation/v1.0.0/model_revision_reproducibility.json`.

The process intentionally optimizes precision and auditability over apparent coverage. A high abstention rate is evidence about taxonomy coverage, not a pipeline failure.
