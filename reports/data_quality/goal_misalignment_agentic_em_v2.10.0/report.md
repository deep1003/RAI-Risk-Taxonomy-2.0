# Goal-Misalignment-to-Agentic constrained EM review — v2.10.0

## Technical summary

The algorithm evaluated all 149 v2.9.0 L4 cards assigned to Goal Misalignment against Goal Misalignment and the four new Agentic L3 nodes. Keyword-gated constrained spherical EM converged after two iterations: five cards moved on iteration 1 and no cards moved on iteration 2. Goal Misalignment decreases from 149 to 144 cards. Three cards move to Goal & Planning and two to Oversight & Control; no card meets the direct-mechanism requirement for Tool Calling or Memory. All five proposed remaps remain `HOLD` pending human review.

## Proposed remaps

| L4 ID | Risk | Proposed L3 | Composite margin |
|---|---|---|---:|
| `RAI4-0480` | Agent task drift | Goal & Planning | 0.157 |
| `RAI4-1130` | Misaligned consequentialist reasoning | Goal & Planning | 0.071 |
| `RAI4-1235` | Goal misgeneralization | Goal & Planning | 0.119 |
| `RAI4-1323` | Alignment risks | Oversight & Control | 0.075 |
| `RAI4-1431` | Uncorrectable harmful goal pursuit | Oversight & Control | 0.094 |

## Scope and baseline

- Source release: v2.9.0, including the preceding Anthropomorphism review.
- Population: every card whose `primary_l3_id` is `RAI3-G-SYS-08` (149 of 1,711 L4 cards).
- Candidate partition: Goal Misalignment, Goal & Planning, Tool Calling, Memory, and Oversight & Control.
- Fixed anchors: cards already assigned to the four Agentic L3 nodes.
- Protected data: all cards outside the 149-card population and all 182 Physical AI locks.

## Method

Each candidate score is

`0.60 × centroid cosine + 0.30 × L3-definition cosine + 0.10 × direct-mechanism keyword signal`.

A destination must exceed Goal Misalignment by at least 0.02. Generic occurrences of *goal*, *objective*, *reward*, *alignment*, *tool*, *memory*, or *control* are insufficient. Goal & Planning requires an agent or assistant coupled to multi-step planning, instrumental subgoals, active objective pursuit, or goal misgeneralization. Tool Calling requires agent-mediated external tool execution. Memory requires persistent agent state across steps or sessions. Oversight & Control requires veto, override, interruption, corrigibility, or shutdown-resistance mechanisms.

After each E-step, centroids are recomputed from fixed destination anchors and newly assigned cards. The algorithm stops at zero assignment changes.

## Robustness and data quality

- Mean selected-score objective increased from 0.645208 to 0.646302.
- A second complete execution produced the identical `cards.json` SHA-256.
- All 1,711 L4 IDs remain unique and assigned.
- No card outside Goal Misalignment changed path.
- All 182 Physical AI cards remain locked.
- Every L4 card retains at least one reference.
- All five moved cards retain `decision_required=true`.
- The full repository suite passes 53 of 53 tests.

## Interpretation and limitations

`RAI4-0480`, `RAI4-1130`, and `RAI4-1235` explicitly describe multi-step agent planning, instrumental subgoals, or an agent actively pursuing a deployment objective. `RAI4-1323` and `RAI4-1431` explicitly include shutdown or correction resistance, making Oversight & Control more specific than generic goal mismatch.

The algorithm favors precision over recall. Reward hacking, proxy objectives, and value disagreement remain in Goal Misalignment when the card does not establish an Agentic execution mechanism. The five moves are diagnostic proposals rather than approved ground truth.

## Recommended next step

Review the five cards against their cited sources, with particular attention to whether `RAI4-1323` should be split into separate goal-pursuit and shutdown-resistance mechanisms. Publish v2.10.0 only after confirming or reverting each proposed move.
