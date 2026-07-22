# v2.17.0 release notes

Date: 2026-07-22

## Scope

- Promoted the guarded v2.17 release candidate to `public/data/releases/v2.17.0`.
- Preserved all 182 Physical AI cards without path changes.
- Applied the non-Physical L4 definition revision pass from the Claude review work.
- Published the site against `v2.17.0`.
- Recompiled the English Technical Report PDF on Mac TeX.

## Data changes

- L4 cards: 1,711 unique cards.
- HOLD cards: 734.
- Primary HOLD paths:
  - General HOLD: 639.
  - Agentic HOLD: 95.
- Non-HOLD semantic cards: 977.
- Guarded reassignment proposals: 22.
  - Actual primary semantic moves before HOLD-path normalization: 14.
  - Existing HOLD semantic-path updates: 8.
- The 14 newly held cards are now placed under the corresponding General or Agentic HOLD path, with the proposed semantic L3 preserved in `hold_semantic_path`.

## BGE-M3 rerun

- Encoder: local pinned BGE-M3 snapshot `5617a9f61b028005a4858fdac845db406aefb181`.
- Output: `reports/validation/v2.17.0/audit_bge/`.
- Unguarded constrained-EM candidates: 151.
- Candidate generation converged after six non-zero update passes plus one zero-move pass.
- Reliability EM convergence:
  - All cards, post-audit: 25 iterations, objective 0.801.
  - HOLD excluded, post-audit: 12 iterations, objective 0.802.
- Post-audit top-1 containment:
  - All cards: 69.5%.
  - HOLD excluded: 79.3%.
- Post-audit perturbation stability at sigma 0.05:
  - All cards: 74.0%.
  - HOLD excluded: 80.0%.

## Interpretation

The BGE-M3 rerun supports the same release conclusion used in the Technical Report: the taxonomy is suitable for public review and navigation, but the consolidated L3 assignment is not treated as human-approved ground truth. HOLD exclusion improves the measured semantic geometry because it removes cards already marked for taxonomic review.
