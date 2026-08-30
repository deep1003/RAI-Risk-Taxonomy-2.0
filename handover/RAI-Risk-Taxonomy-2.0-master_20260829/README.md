# RAI Risk Taxonomy 2.0 Master Handover

Release date: 2026-08-29  
Git commit: `8a948f8`  
Public site: <https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/>

## Final release

- L1: 3 domains
- L3: 49 categories
- L4: 629 cards
- General AI: 487 cards
- Agentic AI: 65 cards
- Physical AI: 77 cards
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
- AC-03: Annotated 237 cards with the verbatim human-review comments and their application results (`human_reviews` in cards.json; two new CSV columns). Cleaned the Mapping provenance display (Korean labels instead of pipeline codes). Fidelity audit: 246 applied / 3 partial / 2 not applied — see HUMAN_COMMENT_FIDELITY_REPORT.
- AC-05: Populated the two empty L3 categories. G_SYS_OREF (over-refusal): axis split from A_SYS_GOAL_022 plus two new cards grounded in XSTest, OR-Bench and AgentHarm. P_INT_TAMPER (physical tampering): sensor spoofing card transferred from G_SYS_SECADV plus two new cards grounded in Cao et al. (CCS 2019), NIST SP 800-82r3 and SP 800-193. Every added or changed card carries verified reference links (References column / dialog section). Card total 720 -> 725.
- AC-06: Added one literature-grounded card each to the two under-populated L3s (G_SYS_INCONS: prompt-format output variability, Sclar et al. ICLR 2024; A_SYS_SELFCOR: intrinsic self-correction failure, Huang et al. ICLR 2024) and absorbed 16 consensus-redundant cards in G_SOC_GOV (-10) and G_INT_UNETH (-6) per two independent reviewers. Card total 725 -> 711.
- AC-07: MECE curation across all 46 L3 categories by two independent reviewers (consensus only): 64 within-L3 duplicates absorbed into representatives, 18 weakly-attributed cards reattributed to their proper L3 (new IDs; old IDs retired), 2 cards removed. Card total 711 -> 645.
- AC-08: Decomposed 18 consensus composite cards (two independent reviewers): 17 retired with meaning fragments absorbed into existing detail cards (lineage unions distributed); G_INT_SELF_004 sharpened to the encouragement axis and G_INT_SELF_008 (failure to respond to self-harm/suicide crisis signals) added, grounded in Moore et al., ACM FAccT 2025. Card total 645 -> 629.
