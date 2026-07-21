# Data dictionary

## Identity and placement are separate

`l4_registry.json` stores permanent card identity, labels, definitions, metrics, and references. It never stores a current L3.

`placements.json` stores the release-specific relationship between one L4 and one L3, or an explicit abstention.

`source_crosswalk.json` connects permanent RAI4 IDs to source-system IDs. One RAI4 can have multiple source rows.

Physical cards also preserve the original raw `three_h_one_r_raw` string, a parsed `three_h_one_r` list with axis and Primary/Secondary fields, and all Physical reference/justification rows inside `references`.

## Placement states

- `locked_physical`: approved Physical AI gold placement; not an algorithmic prediction
- `algorithm_proposed`: strict BGE-M3/rule proposal approved for the exact L3 by both independent frontier expert reviewers; still provisional and not human-approved
- `human_approved`: reserved for a later human validation release
- `needs_taxonomy_decision`: no forced placement; `primary_l3_id` is null

## Confidence

The numeric `confidence` field in v1.0.0 is an uncalibrated ranking score. It is explicitly paired with `confidence_calibrated: false` and must not be interpreted as a probability of correctness.

## Legacy reference fields

Legacy L1-L3 values appear only in post-hoc coverage files whose column names end in `reference_only`. Those values were not included in BGE, local small-model sensitivity prompts, or frontier expert-review packets.

## Version behavior

- L4 ID, source crosswalk, and released snapshots are immutable.
- A later approved remapping changes only the placement relationship.
- Every post-publication placement change requires an append-only migration event.
- Removed or merged IDs are never reused.
