# Release figures

Every figure here is regenerated from the released artifacts by
`projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/regenerate_release_figures_20260830.py`,
which reads only the card CSVs, `manifest.json`, `final_release_qa.json` and
`Audit_Correction_Log.csv`. Running the script again reproduces the set.

House style: Times New Roman, Nature figure geometry (89 mm single column,
183 mm double column, 5-7 pt labels, no grid, colour-blind-safe palette, 300 dpi).
Categorical charts carry the global mean as a dashed grey reference line.
Labels are in English because the Korean and English Technical Reports share one
figure set.

## Current release (629 cards)

| Figure | Shows | Basis |
|---|---|---|
| `domain_counts_before_after.png` | Cards per domain, previous release against the audited release | 798 → 629 |
| `round2_domain_counts.png` | Net change per domain over the same interval | −143 / −9 / −17 |
| `cleaning_reconciliation.png` | Waterfall closing the card count | 798 − 15 − 177 + 23 = 629 |
| `mapping_method_by_domain.png` | Retained EM and HD labels per domain | EM 334 / HD 295 |
| `largest_l3_categories.png` | Ten largest L3 categories in each domain | 46 L3s, each ≥ 3 cards |
| `audit_consolidation_by_correction.png` | Net card change contributed by each audit correction | AC-01 to AC-08 |
| `audit_corrections_trajectory.png` | Card count across the corrections | 777 → 629 |
| `human_review_recovery_domain_counts.png` | Final cards per domain | 487 / 65 / 77 |

`audit_corrections_trajectory.png` and `human_review_recovery_domain_counts.png`
were produced by AC-09, are already correct on the 629 basis, and are the two
figures the Technical Reports embed; they are left untouched so the delivered
PDFs stay valid.

## Stage record

| Figure | Shows |
|---|---|
| `human_review_recovery_actions.png` | Round-2 approved reviewer actions (REMAP 80, REWRITE_KEEP 39, SPLIT 19, MERGE 14, DELETE 14), before the audit |

## Retired

`archive_pre_audit/` holds the figures that cannot be rebuilt on the 629 basis,
with the reason for each in its own README. They depend on EM or Hybrid EM
scores, on similarity scores, or on mapping score status, none of which are
published: AC-04 and AC-10 removed those columns from the release, AC-12
withdrew score status from publication, and rerunning EM is not permitted. Two
further figures were retired because they carry no information at the current
state: the validation chart would be five identical PASS bars, which the
Validation Record table already states with evidence, and the copyedit chart
would be two zeros.
