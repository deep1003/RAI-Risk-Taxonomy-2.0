# Human L3 Review Logs

Each website card exposes its two highest ranked non-Others L3 candidates. A reviewer selects one candidate by opening a prefilled GitHub Issue and submitting it under their GitHub identity.

The daily workflow validates each issue against the current release snapshot, keeps only the latest vote by one reviewer for one card, and publishes aggregate statistics and majority recommendations in this directory.

No workflow or script in this directory changes the taxonomy. `majority_recommendations.json` and `.csv` are non-binding review outputs. Reassignment is permitted only after the user explicitly instructs Codex to analyse the logs and apply the result.

Default majority eligibility requires at least three unique reviewers, a strict majority above 50%, and no tie. Votes from stale release snapshots or choices outside the card's two displayed candidates are rejected but retained in the audit log.
