# RAI Risk Taxonomy 2.0 v2.12.0 — Assignment Reliability Validation

## Overall assessment

**Share with caveats.** The released 54-family taxonomy has statistically
non-random semantic structure, and the HOLD marker separates a materially
weaker review queue. Strong global L3 assignment reliability is nevertheless
not demonstrated.

## Scope and procedure

- Population: all 1,711 released L4 cards and all 54 L3 families.
- Protected subset: the 182 Physical AI paths are measured but never remapped.
- Representation: 1,024-dimensional, unit-normalized BGE-M3 embeddings of
  bilingual labels and definitions.
- Algorithm: seed-initialized spherical EM with nearest-centroid E-steps,
  normalized-mean M-steps, and seed fallback for empty families.
- Validation: objective and reassignment convergence; top-k containment;
  matched-family-size permutation testing with 5,000 repeats; and isotropic
  Gaussian perturbation testing with 200 repeats per sigma.
- Reproducibility: random seed 20260721. Cached embeddings were reused only
  after exact ordered-text SHA-256 fingerprint validation.

## Principal findings

| Measure | Result |
|---|---:|
| Published mean within-family cosine | 0.7703 |
| Median assignment margin | 0.0123 |
| Top-1 / top-3 / top-5 containment | 64.6% / 86.1% / 93.3% |
| Permutation null mean | 0.7389 |
| Permutation p-value, plus-one | 0.0002 |
| Perturbation agreement, sigma 0.01 / 0.05 | 94.5% / 72.9% |
| EM fixed point | 23 iterations |
| EM agreement with released paths | 20.4% |
| ARI / NMI | 0.113 / 0.410 |

The EM objective rose monotonically from 0.663 to 0.802, but its fixed point
proposed 1,362 path changes. Convergence therefore establishes numerical
stability of the optimization, not correctness of the released taxonomy.

## Policy-subset diagnostics

| Subset | Cards | Median margin | Top-1 | Top-3 |
|---|---:|---:|---:|---:|
| Physical locked | 182 | 0.038 | 89.0% | 97.3% |
| Non-Physical | 1,529 | 0.010 | 61.7% | 84.8% |
| HOLD | 689 | 0.004 | 56.2% | 82.4% |
| Non-HOLD | 1,022 | 0.018 | 70.4% | 88.6% |

HOLD top-1 containment is 14.2 percentage points lower than non-HOLD, and its
median margin is less than one quarter as large. This supports HOLD as a
review-priority marker, not as a separate taxonomy or proof of misassignment.

## Decision

- Four-family Agentic expansion: **pass with review**.
- Full 54-family assignment: **not yet demonstrated as strongly reliable**.
- Physical AI authority: preserve all 182 locked paths independently of the
  embedding diagnostic.
- Recent algorithmic changes: retain HOLD until expert adjudication.

Machine-readable results are in `reliability_summary.json`,
`per_l3_metrics.json`, and `em_trace.json`. The integrated journal-style report
is `reports/pdf/rai_risk_taxonomy_technical_report_2_0_en.pdf`.
