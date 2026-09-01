# AC-19 Physical AI minimum corrections

## Scope

Only three user-approved corrections were applied. No card was deleted, merged, split, or newly created. EM and Hybrid EM were not run.

## Decisions

1. `P_SYS_HARDWARE_001` was reidentified as `G_SYS_PERF_017` and moved to `G_SYS_PERF`, because its causal mechanism is deployment performance degradation under sensor and distribution drift rather than physical breakage or wear of hardware.
2. `P_INT_TAMPER_001` was reidentified as `G_SYS_SECADV_061` and moved to `G_SYS_SECADV`, because sensor spoofing and signal injection are adversarial-input attacks explicitly covered by that L3 and excluded from the physical-tampering boundary.
3. `P_SYS_HARDWARE_003` retained its hierarchy and ID, while the mistranslation `우주선(cosmic ray)` was corrected to `우주 방사선(cosmic ray)`.

## Integrity controls

The 50-row L3 master remained byte-identical. Source row IDs, source IDs, facet and act-type attributes, bilingual titles and definitions, and review lineage were preserved. The final release remains 623 cards with domain counts 494 General, 66 Agentic, and 63 Physical.
