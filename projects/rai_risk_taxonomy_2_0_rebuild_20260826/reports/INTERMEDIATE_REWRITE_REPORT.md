# RAI Risk Taxonomy 2.0 Rebuild: Intermediate Report

## Stop point

This rebuild is intentionally stopped after L4 risk eligibility review, deletion, merge, split, and bilingual risk-text rewriting. EM mapping, final L3 assignment, ID reissuance, release CSV generation, website update, commit, and push have not been performed in this rebuild stage.

## Processing result

| Item | Count |
|---|---:|
| Frozen source L4 rows | 892 |
| Deleted rows | 47 |
| Merged-away rows | 20 |
| Split child net increase | 1 |
| Rewritten pre-mapping L4 cards | 826 |
| General target-domain cards | 610 |
| Agentic target-domain cards | 85 |
| Physical target-domain cards | 131 |

Eligibility decisions: {'REWRITE_KEEP': 489, 'KEEP_AS_IS': 337, 'DELETE_NON_RISK': 8}. The rewrite ledger contains 825 changed records.

## Text standardisation applied

- Korean titles end in `리스크`, `위험`, `위해`, `피해`, or `침해`.
- Korean definitions end in the same risk vocabulary and state an adverse outcome.
- English definitions use the causal form `The risk that ...`.
- Topic-only or ordinary application-context cards are removed unless a defensible AI risk mechanism can be reconstructed without inventing a new risk.
- Human-edited descriptions are retained when valid, then normalised for bilingual scope and tone.
- The frozen L3 master is not modified.

## Structural validation

| Check | Result |
|---|---:|
| Missing title/definition fields | 0 |
| Korean titles with invalid ending | 0 |
| Korean definitions with invalid ending | 0 |
| English definitions outside causal form | 0 |
| Duplicate bilingual titles | 0 |
| Duplicate source row IDs | 0 |
| Long unspaced Hangul flags | 0 |

## Review artefacts

- `02_working/L4_Risk_Text_Rewritten_PreMapping.csv`
- `02_working/Risk_Eligibility_Audit.csv`
- `02_working/Rewrite_Ledger.csv`
- `02_working/Deleted_Archive.csv`
- `02_working/Merged_Archive.csv`
- `02_working/Split_Lineage.csv`
- `02_working/Transformation_Log.csv`

Primary rewritten CSV SHA-256: `f2f239e6f485a7c99e3d3d9cd568c61c1706a5a7a3fcbc9bd0cb1bc149494a37`.

## Pending after human review

1. Approve or revise the rewritten L4 names and definitions.
2. Freeze the approved rewritten set.
3. Generate domain-constrained L3 candidates and run EM.
4. Route ambiguous or multi-mechanism cards to domain-specific Others with HD reasons.
5. Reissue L4 IDs, validate the five release CSVs, update reports and website, then commit and push only after approval.
