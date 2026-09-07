# Human L3 Review Logs

Releases that enable L3 voting expose two ranked non-Others L3 candidates on each website card. A reviewer selects one candidate by opening a prefilled GitHub Issue and submitting it under their GitHub identity. The current golden-set release does not display EM scores or review candidates, so it does not accept new candidate votes.

The daily workflow validates each issue against the current release snapshot, keeps only the latest vote by one reviewer for one card, and publishes aggregate statistics and majority recommendations in this directory.

No workflow or script in this directory changes the taxonomy. `majority_recommendations.json` and `.csv` are non-binding review outputs. Reassignment is permitted only after the user explicitly instructs Codex to analyse the logs and apply the result.

Default majority eligibility requires at least three unique reviewers, a strict majority above 50%, and no tie. Votes from stale release snapshots or choices outside the card's two displayed candidates are rejected but retained in the audit log. When the public card payload omits internal `source_row_id` provenance, the workflow resolves historical votes through the immutable source-to-output lineage ledger. Ambiguous split lineage is rejected rather than guessed.
