# Two-Reviewer Diagnosis of Limited Assignment Reliability

## Review status

Two independent specialist agents reviewed the v2.12.0 reliability artefacts.
Reviewer A assessed the statistical estimands, BGE-M3 representation, spherical
EM, permutation test, and perturbation design. Reviewer B assessed the L3
ontology, family boundaries, definition provenance, Physical locks, and HOLD
policy. This is a specialist-agent analytical review; it is not a human
gold-standard adjudication.

## Consensus finding

The limited headline values arise from a combination of ontology mismatch,
family heterogeneity, data provenance, and evaluation design. They cannot be
interpreted as a single classification-accuracy estimate.

1. **Top-1 containment (64.6%) is in-sample.** Released cards contribute to the
   centroids used to score their released paths. Singleton families are
   mechanically self-matching, while large heterogeneous families dominate the
   micro-average.
2. **Perturbation agreement (72.9% at sigma 0.05) is not calibrated model
   reproducibility.** It measures winner stability under synthetic correlated
   score noise. The perturbation scale is about four times the median released
   margin of 0.0123.
3. **EM agreement (20.4%) is not an error complement.** Unconstrained spherical
   EM optimizes a different objective from a normative, hierarchical taxonomy
   and contains no Physical lock, causal-mechanism, family-size, or multi-label
   constraint.
4. **Permutation significance establishes structure, not validity.** Cohesion
   exceeds the matched-size null by 0.0314, with a normalized gain of roughly
   12.0% above the null baseline and plus-one p=0.0002.

## Ontological and provenance diagnosis

- L3 combines harm content, failure mechanisms, rights, governance processes,
  and interaction dynamics. Multi-axial L4 cards are forced into one primary
  path, producing legitimate boundary overlap.
- Family sizes range from 1 to 234. Across the 54 families, size correlates
  negatively with top-1 containment (r=-0.70) and median margin (r=-0.52).
- Anthropomorphism contains 234 cards, 229 of which are HOLD; 173 lack an
  established anthropomorphic mechanism. Goal Misalignment contains 144 cards
  and has a negative median margin.
- Taxonomy gaps, unestablished Anthropomorphism mechanisms, and overloaded or
  low-fit destinations account for 591/689 HOLD cards (85.8%).
- Among 1,529 non-Physical cards, 1,510 use the
  `source_mechanism_only_v2.7` definition form and 1,528 cite exactly one
  reference. Removal of explicit taxonomy scaffold prose does not itself prove
  direct source entailment.
- Physical AI is an authoritative locked stratum and has many very small
  families. Its 89.0% in-sample top-1 containment is not an unbiased comparison
  with algorithmically assigned non-Physical paths.

## Falsifiable follow-up tests

1. Independently code a stratified sample with required primary and optional
   secondary L3 labels. Test whether multi-mechanism judgments concentrate
   among low-margin cards.
2. Replace self-including centroids with leave-one-out or held-out prototypes;
   report macro/micro estimates and confidence intervals.
3. Blind-review contrast sets for the most overlapping L3 pairs using explicit
   inclusion and exclusion rules.
4. Conduct direct source-entailment review and compare expert agreement before
   and after definition rewriting.
5. Calibrate perturbation using paraphrase, translation, truncation, field-order,
   and encoder-version variation rather than an assumed Gaussian scale.
6. Compare multi-start anchored/constrained EM with unconstrained EM, including
   centroid-to-seed drift, cluster-size collapse, and aligned partition
   stability.

## Agreed decision

Retain **SHARE WITH CAVEATS**. The evidence supports non-random semantic
organization and targeted review prioritization, but not strong global
construct validity, criterion validity, or automatic wholesale remapping.
