#!/usr/bin/env python3
"""Rerun the v2.17 constrained-EM audit and reliability with the canonical BGE-M3 encoder.

Usage with the pinned local snapshot:
    python3 scripts/run_v2_17_audit_pipeline.py \
      /Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181 \
      v2.17.0

The pipeline derives the repository root from this script location and writes
outputs to reports/validation/v2.17.0/audit_bge/. Seed 20260721, max sequence
length 256, batch size 32.
"""
print(__doc__)
