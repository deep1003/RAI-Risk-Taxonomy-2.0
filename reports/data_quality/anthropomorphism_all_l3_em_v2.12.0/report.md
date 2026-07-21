# Anthropomorphism L3 constrained EM remapping report (v2.12.0)

## Technical summary

The definition- and keyword-gated constrained EM model evaluated all 242 cards remaining in `RAI3-G-INT-10 Anthropomorphism`. It converged after two iterations and reassigned 8 cards (3.31%); 234 cards remained. All 8 proposed moves retain `HOLD` pending human review.

## Reassignment results

| L4 ID | Risk | Destination | Composite margin | Keyword cosine |
|---|---|---|---:|---:|
| `RAI4-0056` | Remedy pathway opacity | `RAI3-G-SYS-09` Non-Contestability | 0.050 | 0.040 |
| `RAI4-0134` | Clinical decision-support overreliance | `RAI3-G-SYS-07` Overconfidence | 0.040 | 0.027 |
| `RAI4-0425` | Representational stereotyping | `RAI3-G-INT-04` Hate and Unfairness | 0.049 | 0.058 |
| `RAI4-0498` | Erosion of democracy | `RAI3-G-INT-05` Political Neutrality | 0.073 | 0.048 |
| `RAI4-0879` | Increased vulnerability to misinformation | `RAI3-G-SYS-03` Misinformation/Disinformation | 0.038 | 0.038 |
| `RAI4-0906` | AI-induced strategic instability | `RAI3-G-INT-09` Weaponization | 0.030 | 0.026 |
| `RAI4-1309` | Algorithmic bias | `RAI3-G-INT-04` Hate and Unfairness | 0.044 | 0.016 |
| `RAI4-1614` | AI-enabled cyber operations | `RAI3-G-INT-09` Weaponization | 0.029 | 0.024 |

## Scope and definitions

- Source release: `v2.11.0`
- Source cohort: 242 L4 cards assigned to Anthropomorphism
- Fixed anchors: the other 1,469 L4 cards
- Candidate set: Anthropomorphism plus 29 non-Physical General and Agentic L3 nodes
- Exclusion: every Physical L3 was removed from the destination set; the authoritative 182 Physical cards were locked
- Decision rule: a move required a composite margin of at least 0.020 and TF-IDF keyword cosine of at least 0.015

## Methodology

The constrained spherical EM score was:

`0.60 × current L3 centroid cosine + 0.30 × L3 definition cosine + 0.10 × TF-IDF keyword cosine`.

At each iteration, L3 centroids were recomputed from fixed anchors and currently assigned source cards. Agentic destinations required an explicit agentic execution mechanism. Destination-definition guards required the card to express the target risk's distinctive mechanism, preventing generic words such as “challenge,” “death,” or “data” from triggering a move.

## Limitations and robustness checks

The method is a conservative semantic allocation procedure, not a probabilistic proof of taxonomy validity. Boundary cases without a clearly supported destination remain in Anthropomorphism rather than being force-matched. In particular, explainability-only, synthetic-data-quality, generic accountability, and unspecified physical-death cards were rejected after the unrestricted preliminary pass.

- Iteration 1: 8 changes
- Iteration 2: 0 changes
- Total and unique L4 IDs: 1,711
- Physical paths changed: 0
- Reference records changed: 0
- Cards requiring human review after this pass: all 8 proposed moves

## Recommended next step

Review the eight `HOLD` cards as a single adjudication batch before publication. The local `v2.12.0` release should remain unpublished until that review or an explicit deployment instruction.
