#!/usr/bin/env python3
"""Run only source normalisation, cleanup, and bilingual risk rewriting."""

from pathlib import Path

import run_rebuild_pipeline as pipeline


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "02_working"
    output.mkdir(parents=True, exist_ok=True)
    source = pipeline.normalise_rows()
    cleaned, audits = pipeline.apply_cleaning(source)
    cleaned, audits = pipeline.apply_peer_review(cleaned, audits)
    if (len(source), len(audits["deleted"]), len(audits["merged"]), len(cleaned)) != (892, 48, 20, 825):
        raise AssertionError("Unexpected rewrite-stage record counts")

    pipeline.write_csv(cleaned, output / "L4_Risk_Text_Rewritten_PreMapping.csv")
    pipeline.write_csv(audits["eligibility"], output / "Risk_Eligibility_Audit.csv")
    pipeline.write_csv(audits["rewrites"], output / "Rewrite_Ledger.csv")
    pipeline.write_csv(audits["deleted"], output / "Deleted_Archive.csv")
    pipeline.write_csv(audits["merged"], output / "Merged_Archive.csv")
    pipeline.write_csv(audits["split"], output / "Split_Lineage.csv")
    pipeline.write_csv(audits["transformations"], output / "Transformation_Log.csv")
    pipeline.write_csv(audits["peer_review"], output / "Peer_Review_Acceptance_Ledger.csv")
    print({"source": len(source), "rewritten_pre_mapping": len(cleaned),
           "deleted": len(audits["deleted"]), "merged_away": len(audits["merged"])})


if __name__ == "__main__":
    main()
