# City-scale RAI Risk Taxonomy Space Methodology Review

Date: 2026-07-23

Review target: City-scale co-occurrence and actor-mediated risk-contagion methodology for the RAI Risk Taxonomy Space

## Reviewer A: Complex networks and cascading risk

### Assessment

Conditionally suitable. Replacing a dimension-reduction map with a co-occurrence network is theoretically defensible, but co-occurrence alone does not demonstrate propagation.

### Required revisions

- Use `City-scale AI Risk Co-occurrence and Socio-technical Cascading Propagation` as the main concept.
- Reserve `contagion` for calibrated temporal models.
- Separate human and institutional actors from technical mediators and data objects.
- Preserve event-level context through a typed hypergraph.
- Distinguish E1 association, E2 mechanism-supported pathway, and E3 temporally validated propagation.
- Treat L3 as a taxonomy family, not a dynamical attractor.
- Treat HOLD as a taxonomy-review status, not an automatic network boundary.
- Do not interpret centrality as severity, probability, or causal influence.

### Recommended validation

- Degree-preserving bipartite null model
- Benjamini and Hochberg false discovery rate correction
- Observation-level bootstrap edge stability
- Community and centrality sensitivity analysis
- Temporal holdout and calibration when event-time data exist
- External validation across cities and project types

## Reviewer B: Urban AI and sociotechnical governance

### Assessment

Conditionally suitable and well aligned with the Senseable City Seoul research context. The strongest contribution is a typed Urban AI Risk Observatory that connects L4 risks to urban deployment context, affected groups, lifecycle stages, actors, technical dependencies, and controls.

### Required revisions

- Define a bounded observation as deployment, place, time, affected group, AI task, and lifecycle stage.
- Treat documents and project pages as evidence sources rather than observation units.
- Add L4 logical roles: hazard, failure mode, exposure, outcome, and control failure.
- Separate co-occurrence, mechanistic linkage, and causal transition.
- Add citizen and stakeholder review to the validation design.
- Protect urban imagery, sensor data, mobility traces, and vulnerable-group information through purpose limitation, data minimisation, bounded retention, and re-identification assessment.
- Use synthetic data and digital-twin scenarios before field intervention.

## Adopted methodological resolution

The revised method uses a typed hypergraph whose nodes include:

- active L4 risks;
- human and institutional actors;
- technical mediators;
- data objects;
- urban contexts;
- outcomes;
- controls;
- bounded observation units.

Risk-to-risk projection is used only after support filtering, association normalisation, null-model testing, false-discovery correction, and bootstrap stability assessment.

Directional edges require explicit evidence grades:

| Grade | Meaning |
|---|---|
| E1 | Statistically validated co-occurrence |
| E2 | Mechanism-supported cascading pathway |
| E3 | Temporally validated directional propagation |

The reviewed public interpretation is:

> The RAI Risk Taxonomy Space represents empirically observed associations among L4 risks, sociotechnical mediators, actors, and urban contexts. Co-occurrence edges indicate conditional association rather than causal transmission. The term risk propagation is reserved for directional relationships supported by temporal ordering, an explicit transmission mechanism, and validated evidence.

## Core references

- Battiston, F. et al. (2020). Networks beyond pairwise interactions: Structure and dynamics. *Physics Reports*, 874. https://doi.org/10.1016/j.physrep.2020.05.004
- Boccaletti, S. et al. (2014). The structure and dynamics of multilayer networks. *Physics Reports*, 544. https://doi.org/10.1016/j.physrep.2014.07.001
- Cimini, G. et al. (2022). Meta-validation of bipartite network projections. *Communications Physics*, 5, 76. https://doi.org/10.1038/s42005-022-00856-9
- Kivelä, M. et al. (2014). Multilayer networks. *Journal of Complex Networks*, 2. https://doi.org/10.1093/comnet/cnu016
- Leveson, N. (2004). A new accident model for engineering safer systems. *Safety Science*, 42. https://doi.org/10.1016/S0925-7535(03)00047-X
- NIST (2023). *Artificial Intelligence Risk Management Framework 1.0*. https://doi.org/10.6028/NIST.AI.100-1
- OECD (2022). *OECD Framework for the Classification of AI Systems*. https://doi.org/10.1787/cb6d9eca-en
- Pastor-Satorras, R. et al. (2015). Epidemic processes in complex networks. *Reviews of Modern Physics*, 87. https://doi.org/10.1103/RevModPhys.87.925
- Rasmussen, J. (1997). Risk management in a dynamic society: A modelling problem. *Safety Science*, 27. https://doi.org/10.1016/S0925-7535(97)00052-0
- Tumminello, M. et al. (2011). Statistically validated networks in bipartite complex systems. *PLOS ONE*, 6, e17994. https://doi.org/10.1371/journal.pone.0017994
- UN-Habitat and Mila (2022). *AI and Cities: Risks, Applications and Governance*. https://unhabitat.org/ai-cities-risks-applications-and-governance
