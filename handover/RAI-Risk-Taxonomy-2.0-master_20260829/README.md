# RAI Risk Taxonomy 2.0 Master Handover

Release date: 2026-08-29  
Git commit: `8a948f8`  
Public site: <https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/>

## Final release

- L1: 3 domains
- L3: 49 categories
- L4: 720 cards
- General AI: 564 cards
- Agentic AI: 77 cards
- Physical AI: 79 cards
- Others assignments: 0
- L3 master SHA-256: `e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df`

## Directory structure

- `01_data`: final L1, L1/L2/L3, and three domain-specific L4 CSV files
- `02_reports`: Korean and English Technical Reports in PDF and LaTeX
- `03_validation`: release manifest, validation records, lineage, deletion and semantic-curation logs
- `04_web`: public card data, public manifest, and the release homepage snapshot
- `SHA256SUMS.txt`: integrity checksums for the delivered files

The L3 master is unchanged. No EM or Hybrid EM score is exposed in the public card data. Further remapping or application of human-review votes requires a separate explicit instruction.

## Audit correction (2026-08-29)

- AC-01: Restored the standalone card `G_INT_SELF_007` (Promotion of and concrete assistance for preparatory conduct for suicide) and narrowed `G_INT_SELF_004`, per the hard rule separating suicide preparation from execution (line-by-line audit FAIL-F1, two-reviewer consensus). Card total 777 -> 778. See `03_validation/Audit_Correction_Log.csv`.
- AC-02: Absorbed 58 semantically redundant L4 cards across 8 large L3 categories (two independent reviewers, consensus-only set; representative cards keep the union of lineage). Retired IDs are permanent gaps; no renumbering. Card total 778 -> 720. See `03_validation/Audit_Correction_Log.csv`.
