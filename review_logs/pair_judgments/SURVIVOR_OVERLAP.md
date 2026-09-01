# Survivor-set convergence: flow vs expert consolidation (2026-09-01)

Question: starting from the same Master inventory (1,612 cards), does the
percolation-guided flow, descended to the experts' cardinality, keep the same
cards the expert program kept?

Crosswalk: provenance, not similarity. The expert register's Source_L4_IDs
column carries RAI4 identifiers directly; 740 distinct RAI4 cards back the 808
register rows, 721 remain output-alive after expert deletions. The remaining
872 Master cards were absorbed by the operational consolidation before the
register was drawn.

| flow step | n_flow | human survivors kept | expected by chance | Jaccard | z |
|---|---|---|---|---|---|
| 1 (1,383) | 1,383 | 721/721 | 619 | 0.521 | +14.7 |
| 4 (901)   | 901   | 721/721 | 403 | 0.800 | +32.1 |
| **5 (792)** | 792 | **721/721** | 354 | **0.910** | +36.7 |
| 6 (698)   | 698   | 637/721 | 312 | 0.815 | +32.8 |
| 7 (641)   | 641   | 581/721 | 287 | 0.744 | +30.1 |
| 8 (565)   | 565   | 511/721 | 253 | 0.659 | +27.1 |

Findings.
1. Through five consolidations (820 removals) the flow never eliminated a
   single expert-surviving card: its removals are a strict subset of the
   expert program's 891 removals (872 pre-register + 19 deletions).
   Removal precision vs the expert reference: 820/820 = 100%.
2. Survivor-set agreement peaks exactly at the cardinality-matched state
   (F5 = 792 vs 721 expert survivors; Jaccard 0.910), and degrades once the
   flow descends past it (steps 6-8 begin consuming expert survivors) --
   the same boundary at which the pair-judgment experiment shows merge
   precision collapsing.
3. Caveats: both processes read the same BGE-M3 geometry (shared-encoder
   confound; the expert pipeline used similarity proposals with normative
   vetoes and expert adjudication, the flow is fully automatic), and the
   comparison covers the 44.7% of the Master traceable to the register.
   Pairwise merge agreement among surviving representatives is a separate,
   much weaker signal (pair F1 <= 0.10 at steps 6-8), consistent with the
   pair experiment: the flow finds the same redundancy, not the same
   fine-grained merge partition.
