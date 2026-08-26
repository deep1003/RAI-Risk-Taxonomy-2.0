# RAI Risk Taxonomy 2.0 master release

This reviewed master release contains the five canonical CSV artifacts, two
bilingual technical reports, five result figures, and the final QA record.

## Release summary

- L1 domains: 3
- L2 dimensions: 3
- L3 categories: 49, comprising 46 immutable master categories and 3 derived Others categories
- L4 risk cards: 834
- EM assignments: 769
- HD/Others assignments: 65
- Cleaning reconciliation: 892 source rows minus 39 deletions minus 20 absorbed merge rows plus 1 net split addition equals 834 final rows
- Post-build validation: 18 passed, 0 failed

## Canonical CSV files

- `data/L1_Master.csv`
- `data/L1_L2_L3_Master.csv`
- `data/L4_General.csv`
- `data/L4_Agentic.csv`
- `data/L4_Physical.csv`

The source-defined fields of all 46 L3 master rows are preserved exactly. The
three domain-specific Others categories are derived routing categories for
records requiring human decision and do not modify the L3 master source.

## Reports and validation

- `reports/technical_report_ko.pdf`
- `reports/technical_report_en.pdf`
- `validation/final_release_qa.json`
- `manifest.json`

The release manifest records source, model, and primary-output SHA-256 hashes.
