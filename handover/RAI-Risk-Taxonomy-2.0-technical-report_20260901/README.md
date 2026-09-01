# RAI Risk Taxonomy 2.0 Technical Report Handover

Handover date: 1 September 2026

This package contains the final English integrated technical report, its Overleaf source bundle, the public taxonomy CSVs used by the report, and the principal review and validation tables.

## Final report

- Title: *RAI Risk Taxonomy 2.0: An Auditable Human-in-the-Loop Pipeline for Consolidating, Splitting, and Reassigning AI Risk Cards*
- Length: 19 pages
- Final L4 total: 623
- Domain totals: General AI 494, Agentic AI 66, Physical AI 63
- Substantive L3 categories: 47
- Others assignments: 0

## Authors

1. Youngsam Chun, joint first author and corresponding author
2. Sooyoung Kim, joint first author
3. Yunjin Park
4. Jungwon Yoon
5. Jihwan Chang
6. Jinhee Jeong
7. Jaehyun Kim

## Directory structure

- `01_data`: final public L1, L1/L2/L3, and three domain-specific L4 CSV files
- `02_report`: final PDF, LaTeX manuscript, and bibliography
- `03_overleaf`: complete Overleaf-ready ZIP with figures, tables, data, and build script
- `04_analysis_validation`: source inventory, hierarchy summaries, three-round algorithm-human integrity table, and Round 2 and Round 3 decision ledgers
- `SHA256SUMS.txt`: SHA-256 checksums for every handover file except the checksum file itself

## Methodological caveats

- Only Round 1 is a direct algorithmic Top-1 versus adjudicated-L3 comparison. Rounds 2 and 3 are incremental audits of mappings that already contain prior human decisions.
- EM and Hybrid EM were not rerun on the current 623-card wording and hierarchy.
- The report discloses two stale public L2 fields, `A_SYS_GOAL_023` and `A_SYS_AUTH_024`, as release-schema QA items. They were not silently corrected during report preparation.

## Compilation

Extract the ZIP in `03_overleaf`, upload the resulting directory to Overleaf, and select XeLaTeX. For a local build:

```bash
latexmk -xelatex -bibtex main.tex
```

