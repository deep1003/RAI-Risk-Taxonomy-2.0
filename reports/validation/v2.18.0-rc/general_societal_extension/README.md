# General AI Societal Impact Extension Validation

Release candidate: `v2.18.0-rc`
Source release: `v2.17.2`
Validation date: 2026-07-25

## Scope

- 1,711 registered L4 IDs preserved
- 1,660 active cards preserved
- 51 retired records preserved
- 54 semantic L3 families
- 56 active L3 paths when the two review paths are included
- 181 listed candidate IDs, including 179 active and 2 retired records
- Physical AI System Safety and Interaction Safety assignments locked
- Existing mappings outside the listed candidates and the former Physical AI
  Societal Safety path locked

## Hierarchy changes

| Type | ID | English | Korean |
|---|---|---|---|
| New L2 | `RAI2-G-SOC` | Societal Impact | 사회적 파급 |
| New L3 | `RAI3-G-INT-12` | Energy Consumption and Environmental Pollution | 에너지 소비 및 환경 오염 |
| New L3 | `RAI3-G-SOC-10` | Accountability and Governance Gaps | 책임성 부족 및 거버넌스 체계 부재 |
| New L3 | `RAI3-G-SYS-10` | Lack of Transparency | 투명성 부족 |
| New L3 | `RAI3-G-SOC-11` | Fairness | 공정성 |

The nine former `RAI3-P-SOC-01` through `RAI3-P-SOC-09` families were
migrated to `RAI3-G-SOC-01` through `RAI3-G-SOC-09`. Their definitions,
references, legacy identifiers, and Physical AI origin are retained.

## Assignment method

The assignment score is:

`0.60 × L3 centroid cosine + 0.30 × L3 definition cosine + 0.10 × TF-IDF keyword cosine`

The higher-scoring admissible L3 wins. The procedure converged after four
iterations. A listed HOLD card was released only when both criteria were met:

- direct L4-to-L3 seed cosine at least 0.45
- winner-to-runner-up composite margin at least 0.015

## Results

| Result | Count |
|---|---:|
| Active cards changed | 182 |
| HOLD cards released | 151 |
| Former Physical societal cards structurally moved | 30 |
| Other non-HOLD competitive moves | 1 |
| HOLD cards retained | 614 |
| Retained because outside this extension scope | 588 |
| Retained because the release threshold was not met | 26 |

The only non-HOLD competitive move outside the structural migration was
`AI water and resource use (RAI4-0463)` from Agentic Destabilising Dynamics
to `Energy Consumption and Environmental Pollution`.

## New L3 active-card counts

| L3 | Active L4 cards |
|---|---:|
| Energy Consumption and Environmental Pollution | 26 |
| Accountability and Governance Gaps | 25 |
| Lack of Transparency | 31 |
| Fairness | 22 |

## Migrated L3 active-card counts

| L3 | Active L4 cards |
|---|---:|
| Privacy Violations | 5 |
| Labor Displacement | 6 |
| Socioeconomic Inequality | 1 |
| Power Concentration | 1 |
| Bias & Discrimination | 19 |
| Lack of Accountability & Liability | 12 |
| Lack of Transparency, Explainability & Trust | 1 |
| Unhealthy / Dangerous Human-EAI Relationships | 4 |
| Transformative Effects | 2 |

## Rollback

The complete source release is sealed at:

`archives/sealed/v2.17.2_pre_general_societal_extension_20260725.tar.gz`

The archive hash, source-file hashes, source commit, and restore command are
stored in the adjacent manifest. A test extraction reproduced every source
file hash.

## Release status

This is a release candidate pending human validation. The local website,
Semantic Space, Technical Report, and release metadata point to
`v2.18.0-rc`. Online publication requires a separate commit and push.

## HOLD sensitivity

The BGE-M3 sensitivity analysis uses the same 54 semantic L3 families in both
conditions.

| Diagnostic | HOLD included | HOLD excluded |
|---|---:|---:|
| Cards | 1,660 | 1,046 |
| EM iterations | 20 | 12 |
| Final mean cosine objective | 0.8005 | 0.8026 |
| Top-1 containment | 71.9% | 81.6% |
| Noise stability at sigma 0.05 | 75.0% | 80.7% |

Machine-readable results and the comparison figure are stored in
`reports/validation/v2.18.0-rc/hold_sensitivity_bge_m3/`.
