# survivor_overlap.py — does the flow keep the same cards the expert program kept?
# Provenance crosswalk: Human_Review_Instruction_Register.Source_L4_IDs (RAI4 ids)
# joined to Source_Disposition_Ledger (alive iff Output_L4_IDs nonempty).
# Flow states are rebuilt from the Master with the canonical step boundaries.
# Output: per-step survivor overlap, hypergeometric z, Jaccard.
# (Run from the repository root. See review_logs/pair_judgments/ for the
#  companion pair-judgment experiment.)
