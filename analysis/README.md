# Granularity analysis scripts

Analysis code for "Percolation transitions in semantic space determine the granularity of AI risk taxonomies" (manuscript under submission; not included in this repository).

- `flow_canonical.py` — canonical granularity flow: iterated cohesion–attraction crossing with per-step random-group null validation (resumable; writes `data/experiments/review/flow_states.json`).
- `boot1000_sweep.py` — 1,000-replicate subsample sweep of the threshold graph (event-driven union–find).
- `coh_div_sweep.py`, `coh_div_sweep_frac.py` — cohesion/attraction curves and crossing, full inventory and subsample fractions.
- `make_tau_star_panel.py`, `analyze_tau_star_vs_n.py` — density dependence of the crossing.
- `rebuild_figs_v3.py` — manuscript figures.
- `build_flow_review_v2.py` — F1/F4 human-audit pages (EM-based L3 assignment).

All stochastic procedures use fixed seeds recorded in the scripts.
