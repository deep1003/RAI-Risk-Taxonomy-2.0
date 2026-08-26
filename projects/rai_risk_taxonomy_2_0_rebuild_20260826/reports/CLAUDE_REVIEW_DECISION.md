# Claude L4 Review: Critical Acceptance Record

## Decision summary

| Proposal | Decision | Implementation |
|---|---|---|
| R1 L4 specificity | Accepted | Definitions retain a concrete mechanism and affected outcome rather than repeating L3 abstractions. |
| R2 one-sentence risk definition | Accepted | Korean definitions end in a risk term; English definitions retain `The risk that ...`. |
| R3 remove mechanical title suffixes | Partially accepted | Titles use natural L3-style nominal labels. `리스크` or `위험` is retained only where removal would obscure meaning or alter a standard term. |
| R4 additional tracking ID | Functionally accepted | Existing `source_row_id`, `Source_L4_ID`, and `Source_L4_IDs` already provide single, merged, split, and new-card lineage. No redundant identifier was added. |
| R5 row-level legal and guideline basis | Partially accepted | Existing verified terminology-source codes are retained. Unverified or overly broad provision-level attribution was not copied automatically. |
| 713 spacing restorations | Accepted | Korean title and definition spacing was restored from the peer-review alternatives. |
| Eight substantive redefinitions | Accepted with one refinement | All eight were adopted. RAI4-0568 was refined to make AI developer involvement, data-subject rights, and organisational legal liability explicit. |
| Drop RAI4-0853 | Accepted | The category-only, harm-unspecified card was archived and excluded from mapping. |

## Additional critical correction

RAI4-1157 was redefined as cyberattack enablement through vulnerability discovery and exploit writing. Keeping it in Physical AI would contradict the revised mechanism. It was therefore routed to General AI and constrained to `G_SYS_SECADV`, where EM assigned it to Security and Adversarial Robustness Failure.

## Result after rerun

- Final L4 cards: 825
- General: 611
- Agentic: 85
- Physical: 129
- EM assignments: 559
- Others and HD: 266
- Validation: 18 passed, 0 failed
- L3 master: 46 source rows unchanged, plus three derived Others rows

The rebuild produced the five requested release CSVs. Website publication, commit, and push remain separate approval-gated actions.
