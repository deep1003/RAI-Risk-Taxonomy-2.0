# Merge-precision pair experiment — preliminary analysis

Status: PRELIMINARY (2 independent judgments). Generated 2026-09-01.

## Submissions and the independence finding

Six submissions were received through the survey store. The five submissions
JW_01, JH_01, SY_01, YJ_01, YS_01 differ on at most 2 of 135 pairs (two pairs of
response vectors are identical; mean pairwise agreement 0.993 against a
chance expectation of 0.822 given their own marginals). They are therefore not
independent judgments and, by the study lead's decision (2026-09-01), are
collapsed into ONE effective rater (their majority vector). The effective
design is two independent judgments:

- Rater A: Youngsam Chun (134/135 answered)
- Rater B: collapsed cluster (135/135)

The survey remains open; one or two additional independent raters are to be
recruited before the reliability ceiling is finalized.

## Inter-rater reliability (A vs B)

- Raw agreement: 109/134 = 0.813
- Krippendorff alpha (nominal): 0.371
- Disagreement is one-directional: A judges "same" where B judges "distinct"
  in 24 of 25 conflicts, concentrated in strata S1 and S4 (the boundary zone).
  Experts differ in merge threshold, not randomly.

## Flow versus the two-rater consensus (n = 109)

- Merge precision 0.131 (8/61), merge recall 0.727 (8/11), accuracy 0.486
- By stratum (consensus verdicts):
  - S1 crossing merges: same 7 / distinct 18
  - S2 chained merges (steps 2-5): same 1 / distinct 35
  - S3 cosine-matched non-merges: same 0 / distinct 40 (unanimous endorsement of separations)
  - S4 boundary-adjacent non-merges: same 3 / distinct 5 (P001, P030, P048 are confirmed misses)

## Reading

1. The flow's SEPARATION decisions are fully endorsed (S3 40/40).
2. Chained merges (steps 2-5) are rejected almost entirely: consolidation at
   F4/F5 depth is lossy compression of adjacent-but-distinct risks, not
   deduplication. This matches the manuscript's own chaining diagnosis.
3. Even crossing merges are only partially endorsed; identity-preserving use
   should stop near F1-F2.
4. The human ceiling itself is low (alpha = 0.37): experts disagree
   systematically at the boundary, which is the paper's motivating claim.

## Provenance

Raw submissions: this directory (per-rater JSON, all_judgments.csv).
Answer-key fingerprint: data/experiments/review/pair_survey_key.sha256.
Cluster collapse approved by the study lead; do not report the six-rater
alpha (0.692) as an independent-rater statistic.
