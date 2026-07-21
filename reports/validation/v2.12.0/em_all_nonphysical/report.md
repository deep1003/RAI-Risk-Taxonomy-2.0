# Algorithm 2 validation for all non-Physical L4 risks

## Technical summary

Algorithm 2 is executable at the full non-Physical scale, but its unconstrained output is not reliable enough for automatic publication. Seed-initialized spherical EM evaluated 1,529 L4 cards against 30 General and Agentic L3 families, reached a fixed point after 18 iterations, and increased its cosine objective monotonically. Nevertheless, it agreed with the current mapping on only 30.80% of cards, with ARI 0.149 and NMI 0.351, and proposed 1,058 remaps (69.20%).

## Scope and data integrity

- Release evaluated: `v2.12.0`
- Total unique L4 cards: 1,711 of 1,711
- Authoritative Physical cards excluded and locked: 182
- Non-Physical cards evaluated: 1,529
- Non-Physical L3 candidates: 30
- BGE-M3 cache acceptance: ordered card and L3 text SHA-256 fingerprints matched the cache-source release exactly
- Source taxonomy mutations: none

## Convergence is sound, but taxonomic agreement is weak

The E-step assigned each unit-normalized card embedding to its nearest centroid. The M-step recomputed each centroid as the normalized mean of assigned cards and retained the seed for an empty family. The objective was monotonically non-decreasing and the assignment reached zero changes at iteration 18. No L3 family was empty at the fixed point.

| Diagnostic | Result |
|---|---:|
| Exact agreement with current mapping | 30.80% |
| Adjusted Rand Index | 0.149 |
| Normalized Mutual Information | 0.351 |
| Candidate remaps | 1,058 (69.20%) |
| Current mapping top-1 containment | 62.59% |
| Current mapping top-2 containment | 77.50% |
| Current mapping top-3 containment | 85.48% |
| Current mapping top-5 containment | 93.26% |
| Current median assigned-vs-alternative margin | 0.010 |

The very low median margin and 37.41% negative-margin share indicate extensive geometric overlap among current L3 definitions and card clusters. This does not by itself prove that current cards are wrong: the L3 ontology contains operational distinctions that a single embedding geometry does not encode.

## Cohesion is non-random, but perturbation stability misses the strong threshold

The released grouping has mean within-family cohesion 0.765, above the matched-family-size permutation null mean of 0.738. None of 5,000 permutations equaled or exceeded the observed value; the plus-one p-value is 0.0002. The converged EM grouping is also non-random and has higher geometric cohesion, 0.792, with the same p-value.

However, EM assignment agreement under Gaussian score perturbation falls from 98.99% at sigma 0.01 to 95.04% at 0.025 and 85.20% at 0.05. The Technical Report's strong criterion requires at least 97% through sigma 0.05. This run therefore demonstrates semantic structure but not strong global assignment reliability.

## Why the 1,058 remaps must remain a review queue

Of the proposed remaps, 275 have margin below 0.02, 705 have margin below 0.05, and 351 have per-card stability below 80% at sigma 0.05. Even some large-margin, perturbation-stable results are ontologically invalid: for example, environmental-harm cards can be pulled toward Violence, and software-supply-chain cards can be pulled toward Tool Calling solely because of lexical and embedding proximity.

Pure Algorithm 2 therefore optimizes semantic compactness rather than the full taxonomy policy. It does not enforce:

- L1/L2 compatibility;
- the Agentic-uniqueness requirement;
- authoritative Physical membership;
- destination-specific risk-mechanism keywords;
- reference/evidence compatibility;
- locked expert decisions or human-approved aliases.

## Recommended next step

Keep `candidate_remaps.csv` as a diagnostic queue only. A publishable reassignment pass should use constrained EM: retain Algorithm 2's cosine E/M core, but add L1/L2 admissibility, Agentic-uniqueness gates, distinctive destination-definition evidence, minimum margin and stability thresholds, locked-card constraints, and human review. A conservative first review stratum is the 333 candidates with margin at least 0.05 and sigma-0.05 stability at least 97%, but even these require ontology checks before movement.

## Reproducible artifacts

- Executed notebook: `output/jupyter-notebook/algorithm2_em_l3_nonphysical_validation_v2_12.ipynb`
- Aggregate results: `reliability_summary.json`
- Candidate review queue: `candidate_remaps.csv`
- L3 count shifts: `l3_count_comparison.csv`
- Per-L3 reliability: `per_l3_reliability.csv`
- Convergence trace: `em_trace.csv`
