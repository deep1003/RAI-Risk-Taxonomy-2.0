# RAI Risk Taxonomy 2.0 Master Handover

Release date: 2026-08-29  
Release commit: `8a948f8` (audit corrections AC-01 to AC-12 were applied on top of it)  
Public site: <https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/>

## Final release

- L1: 3 domains
- L3: 50 categories (47 master + 3 Others)
- L4: 629 cards
- General AI: 487 cards
- Agentic AI: 65 cards
- Physical AI: 77 cards
- Others assignments: 0
- L3 master SHA-256: `1ab58e1dd002d85de92db4bb1e49daa744d053a3950025bfe831bdef9bf98c54`

## Directory structure

- `01_data`: final L1, L1/L2/L3, and three domain-specific L4 CSV files
- `02_reports`: Korean and English Technical Reports in PDF and LaTeX
- `03_validation`: release manifest, validation records, lineage, deletion and semantic-curation logs
- `04_web`: public card data, public manifest, and the release homepage snapshot
- `SHA256SUMS.txt`: integrity checksums for the delivered files

The pre-AC-14 L3 master was extended only by the explicitly approved `G_SYS_PERF`; no other L3 definition changed. No EM or Hybrid EM score is exposed in the public card data. Further remapping or application of human-review votes requires a separate explicit instruction.

## Audit correction (2026-08-29)

- AC-01: Restored the standalone card `G_INT_SELF_007` (Promotion of and concrete assistance for preparatory conduct for suicide) and narrowed `G_INT_SELF_004`, per the hard rule separating suicide preparation from execution (line-by-line audit FAIL-F1, two-reviewer consensus). Card total 777 -> 778. See `03_validation/Audit_Correction_Log.csv`.
- AC-02: Absorbed 58 semantically redundant L4 cards across 8 large L3 categories (two independent reviewers, consensus-only set; representative cards keep the union of lineage). Retired IDs are permanent gaps; no renumbering. Card total 778 -> 720. See `03_validation/Audit_Correction_Log.csv`.
- AC-03: Annotated 237 cards with the verbatim human-review comments and their application results (`human_reviews` in cards.json; two new CSV columns). Cleaned the Mapping provenance display (Korean labels instead of pipeline codes). Fidelity audit: 246 applied / 3 partial / 2 not applied — see HUMAN_COMMENT_FIDELITY_REPORT.
- AC-05: Populated the two empty L3 categories. G_SYS_OREF (over-refusal): axis split from A_SYS_GOAL_022 plus two new cards grounded in XSTest, OR-Bench and AgentHarm. P_INT_TAMPER (physical tampering): sensor spoofing card transferred from G_SYS_SECADV plus two new cards grounded in Cao et al. (CCS 2019), NIST SP 800-82r3 and SP 800-193. Every added or changed card carries verified reference links (References column / dialog section). Card total 720 -> 725.
- AC-06: Added one literature-grounded card each to the two under-populated L3s (G_SYS_INCONS: prompt-format output variability, Sclar et al. ICLR 2024; A_SYS_SELFCOR: intrinsic self-correction failure, Huang et al. ICLR 2024) and absorbed 16 consensus-redundant cards in G_SOC_GOV (-10) and G_INT_UNETH (-6) per two independent reviewers. Card total 725 -> 711.
- AC-07: MECE curation across all 46 L3 categories by two independent reviewers (consensus only): 64 within-L3 duplicates absorbed into representatives, 18 weakly-attributed cards reattributed to their proper L3 (new IDs; old IDs retired), 2 cards removed. Card total 711 -> 645.
- AC-08: Decomposed 18 consensus composite cards (two independent reviewers): 17 retired with meaning fragments absorbed into existing detail cards (lineage unions distributed); G_INT_SELF_004 sharpened to the encouragement axis and G_INT_SELF_008 (failure to respond to self-harm/suicide crisis signals) added, grounded in Moore et al., ACM FAccT 2025. Card total 645 -> 629.
- AC-09: Rewrote and recompiled the Korean and English Technical Reports against the 629-card release, refreshed the figures, synchronised every internal snapshot, and removed the Mapping provenance section from the card detail view.
- AC-10: Dropped the human-review and References columns from the published CSVs (25 columns). Both fields remain in this handover's full-column data and in `04_web/cards.json`.
- AC-11: Attached verified literature references to 160 cards. Six proposal agents, two independent reviewers, then a third-party re-verification of all 131 unique URLs against the arXiv and Crossref APIs; claimed titles matched the resolved records 158/158 and no fabricated citation was found.
- AC-12: Release metadata sync. `manifest.json` still reported the pre-audit 777-card figures and was rendering the public Release Manifest page from them, so it now carries the 629-card counts with the round-2 stage figures preserved under `round2_pipeline_historical`; the manifest page's renderer, which failed outright on this release, was repaired; the release README was rewritten to the 629-card state; the two AC-07 removals missing from `Deletion_Tombstones.csv` were added (19 rows, matching the disposition ledger); and `SHA256SUMS.txt`, empty since AC-05, was regenerated over all 23 delivered files. No card data changed.
- AC-14: Created the new L3 category `G_SYS_PERF` (성능·신뢰성 실패 / Performance and Reliability Failure) as explicitly requested in the second-round human review, and reattributed 10 cards to it by two-reviewer consensus (EVAL 6, SECADV 2, CONTEXT 1, OVERCONF 1). Card total unchanged at 629; L3 master now 50 rows and its SHA-256 has changed accordingly.
