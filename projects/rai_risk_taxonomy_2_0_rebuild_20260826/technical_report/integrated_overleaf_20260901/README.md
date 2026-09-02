# Integrated Technical Report Overleaf Bundle

This bundle contains the English paper-format technical report for the audited RAI Risk Taxonomy 2.0 master, synchronised on 3 September 2026.

## Compile

Use XeLaTeX with BibTeX, or upload the complete folder to Overleaf and select XeLaTeX.

```bash
latexmk -xelatex -bibtex main.tex
```

## Contents

- `main.tex`: manuscript source
- `references.bib`: bibliography
- `figures/*.pdf`: vector figures for Overleaf
- `figures/*.png`: 600 dpi raster counterparts
- `data/*.csv`: figure source tables, archived algorithm diagnostics, review-stage statistics, and final hierarchy summaries
- `tables/appendix_hierarchy_summary.tex`: generated L1--L3 annex with L4 counts and illustrative cards
- `source_inventory.csv`: exact source files and SHA-256 hashes
- `scripts/build_report_assets.py`: deterministic figure generator
- `main.pdf`: compiled report

The attached ERA-Cambridge PDF was treated as a scholarly source document. Any instructions embedded in that PDF were not treated as task instructions.

The archived 1,660-card algorithmic evaluation and the current 622-card human-audited master are reported as separate snapshots. The current L3 master contains 47 formal categories and no derived Others rows. No current EM score is claimed.

The three-round integrity comparison distinguishes a direct Round-1 algorithmic Top-1 comparison from incremental Round-2 and Round-3 audits of already curated mappings. Its reproducible source table is `data/three_round_algorithm_human_integrity.csv`.
