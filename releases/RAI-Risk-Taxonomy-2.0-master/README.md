# RAI Risk Taxonomy 2.0 master release

This master release contains five canonical CSV artifacts, bilingual technical reports, result figures, and the final QA record.

## Release summary

- L1 domains: 3
- L2 dimensions: 3
- L3 categories: 49, comprising 46 immutable master categories and 3 derived Others categories
- L4 risk cards: 808
- L4 title terminology normalisations: 66
- Semantic near-duplicate review: 66 candidate pairs, 5 lower-representativeness cards discarded
- General / Agentic / Physical: 599 / 90 / 119
- EM assignments: 612
- HD/Others assignments: 196
- L1-first cross-domain reviews: 30, including 14 retained in the confirmed L1's Others queue because no exact current L3 exists
- L3-referenced AI-technology definition rewrites: 260
- Cleaning reconciliation: 892 source rows minus 65 deletions minus 20 absorbed merge rows plus 1 net split addition equals 808 final rows
- Post-build validation: 50 passed, 0 failed

## Canonical CSV files

- `data/L1_Master.csv`
- `data/L1_L2_L3_Master.csv`
- `data/L4_General.csv`
- `data/L4_Agentic.csv`
- `data/L4_Physical.csv`

All 46 source-defined L3 rows are preserved exactly. The three domain-specific Others categories are derived human-decision queues and do not modify the source L3 master.
Every Korean and English L4 definition explicitly names an AI technology and follows an L3-style risk-statement structure. Each L4 also contains three representative concepts per language and two reviewable non-Others L3 candidates with base and hybrid EM scores.

## Reports and validation

- `reports/technical_report_ko.pdf`
- `reports/technical_report_en.pdf`
- `validation/final_release_qa.json`
- `validation/L1_Cross_Domain_Routing_Audit.csv`
- `manifest.json`
