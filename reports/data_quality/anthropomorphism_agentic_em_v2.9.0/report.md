# Anthropomorphism-to-Agentic constrained EM review — v2.9.0

## Technical summary

The algorithm evaluated all 245 v2.8.0 L4 cards assigned to Anthropomorphism against Anthropomorphism and the four new Agentic L3 nodes. A keyword-gated constrained spherical EM procedure converged after two iterations: three cards moved on iteration 1 and no cards moved on iteration 2. Anthropomorphism decreases from 245 to 242 cards. The proposed v2.9.0 release preserves all 1,711 unique L4 IDs and all 182 Physical AI locks. Every moved card remains `HOLD` pending human review.

## Result

| L4 ID | Risk | Previous L3 | Proposed L3 | Composite margin |
|---|---|---|---|---:|
| `RAI4-0117` | Human veto erosion | Anthropomorphism | Oversight & Control | 0.113 |
| `RAI4-1239` | Situational awareness | Anthropomorphism | Goal & Planning | 0.093 |
| `RAI4-1424` | Risks from AIs developing goals and values that are different from humans | Anthropomorphism | Goal & Planning | 0.068 |

No Anthropomorphism card met the combined mechanism and margin requirements for Tool Calling or Memory.

## Scope and definitions

- Population: all 245 cards whose v2.8.0 `primary_l3_id` is `RAI3-G-INT-10`.
- Candidate partition: Anthropomorphism, Goal & Planning, Tool Calling, Memory, and Oversight & Control.
- Fixed anchors: the 31 cards already assigned to the four Agentic L3 nodes in v2.8.0.
- Protected data: all cards outside the 245-card population and all Physical AI mappings.
- Unit of analysis: one unique L4 risk card.

## Method

For card embedding $x_i$ and candidate family $k$, each EM assignment maximizes

`0.60 × centroid cosine + 0.30 × L3-definition cosine + 0.10 × direct-mechanism keyword signal`.

The destination must also exceed the Anthropomorphism score by at least 0.02. A new Agentic family is eligible only when the card contains a category-specific direct mechanism, such as reward hacking or instrumental subgoals for Goal & Planning, agent-mediated external tool execution for Tool Calling, persistent cross-step state for Memory, or human veto/override failure for Oversight & Control. Generic occurrences of words such as *agent*, *tool*, *memory*, or *control* do not open the gate.

After each E-step, the M-step recomputes normalized family centroids from fixed v2.8 anchors and newly assigned Anthropomorphism cards. Iteration stops at zero changes.

## Robustness and data-quality checks

- EM objective increased from 0.646658 to 0.647098.
- Re-running the complete builder produced an identical SHA-256 for `cards.json`.
- All 1,711 L4 IDs remain unique and assigned.
- No card outside the original Anthropomorphism population changed L3.
- All 182 Physical AI cards remain locked.
- All cards retain at least one reference.
- All three remaps retain `decision_required=true`.
- The repository test suite passes 50 of 50 tests.

## Limitations

The result is a constrained diagnostic, not human ground truth. The keyword gate deliberately favors precision over recall. The `Situational awareness` card is moved because its definition explicitly links situational knowledge to reward hacking and instrumental subgoals; a reviewer may reasonably decide that the label is broader than Goal & Planning. `Human veto erosion` is a strong Oversight & Control fit, but its definition concerns consequential recommendations rather than an explicit autonomous execution loop. These two boundary questions justify retaining HOLD.

## Recommended next step

Human-review the three proposed cards against their cited sources. Publish v2.9.0 only after confirming or reverting each move; do not clear HOLD solely from the EM result.
