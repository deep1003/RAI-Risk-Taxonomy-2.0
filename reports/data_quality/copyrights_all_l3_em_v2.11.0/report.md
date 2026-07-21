# Copyrights L3 constrained EM remapping report (v2.11.0)

## Scope and constraints

- Source release: `v2.10.0`
- Evaluated cards: all 117 cards assigned to `RAI3-G-INT-08 Copyrights`
- Fixed anchors: the other 1,594 L4 cards
- Candidate destinations: 29 non-Physical General and Agentic L3 nodes, plus Copyrights
- Physical lock: all Physical L3 nodes and the authoritative 182 Physical cards were excluded from movement
- Review policy: every moved card remains classified but is marked `HOLD` (`decision_required=true`)

## Method

The constrained spherical EM score is

`0.60 × current L3 centroid cosine + 0.30 × L3 definition cosine + 0.10 × TF-IDF keyword cosine`.

A destination was eligible only when its keyword cosine was at least 0.015 and its final composite score exceeded Copyrights by at least 0.020. Agentic destinations additionally required an explicit agentic execution signal. A destination-definition guard rejected matches caused only by generic shared words. Centroids were recomputed after each E/M pass until no assignment changed.

## Convergence and result

The model converged after 2 iterations: 4 changes in iteration 1 and 0 changes in iteration 2. Four of 117 cards (3.42%) moved; 113 remained in Copyrights.

| L4 ID | Risk | Destination | Composite margin | Keyword cosine |
|---|---|---|---:|---:|
| `RAI4-0586` | Improper data curation | `RAI3-G-SYS-03` Misinformation/Disinformation | 0.030 | 0.041 |
| `RAI4-0620` | Cyber offence | `RAI3-G-INT-09` Weaponization | 0.028 | 0.026 |
| `RAI4-0634` | Large-scale persuasion and harmful manipulation risks | `RAI3-G-SYS-03` Misinformation/Disinformation | 0.033 | 0.018 |
| `RAI4-1051` | Social stereotypes and unfair discrimination | `RAI3-G-INT-04` Hate and Unfairness | 0.058 | 0.035 |

## Quality controls

- Total and unique L4 IDs remain 1,711.
- No Physical card or Physical path changed.
- No card moved into a Physical L3.
- Only the four audited source paths changed.
- References were preserved byte-for-byte at card-record level.
- The remaining 113 Copyrights cards were not force-matched.

This is an unpublished local candidate release. The four remaps require human review before publication.
