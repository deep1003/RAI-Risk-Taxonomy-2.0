#!/usr/bin/env python3
"""Validate GitHub Issue votes and publish daily review statistics.

This script never changes taxonomy assignments. It only exports vote logs,
deduplicates reviewer choices, and produces non-binding majority recommendations.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


SCHEMA = "rai-taxonomy-human-review-v1"
MARKER = f"<!-- {SCHEMA} -->"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def flatten_issues(payload) -> list[dict]:
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        return [issue for page in payload for issue in page]
    return payload if isinstance(payload, list) else []


def extract_payload(body: str) -> dict:
    if MARKER not in (body or ""):
        raise ValueError("SCHEMA_MARKER_MISSING")
    match = re.search(r"```json\s*(\{.*?\})\s*```", body, flags=re.DOTALL)
    if not match:
        raise ValueError("JSON_BLOCK_MISSING")
    value = json.loads(match.group(1))
    if value.get("schema") != SCHEMA:
        raise ValueError("SCHEMA_MISMATCH")
    return value


def iso_date(value: str) -> str:
    return (value or "")[:10]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issues-json", type=Path, required=True)
    parser.add_argument("--cards-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-reviewers", type=int, default=3)
    args = parser.parse_args()

    issues = flatten_issues(load_json(args.issues_json))
    cards_doc = load_json(args.cards_json)
    cards = cards_doc["cards"]
    cards_by_source = {card["source_row_id"]: card for card in cards}

    audit_rows: list[dict] = []
    valid_rows: list[dict] = []
    for issue in sorted(issues, key=lambda item: (item.get("created_at", ""), item.get("number", 0))):
        if issue.get("pull_request"):
            continue
        body = issue.get("body") or ""
        if MARKER not in body:
            continue
        base = {
            "issue_number": issue.get("number"),
            "issue_url": issue.get("html_url"),
            "reviewer": (issue.get("user") or {}).get("login"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
            "state": issue.get("state"),
        }
        try:
            payload = extract_payload(body)
            source_row_id = payload.get("source_row_id")
            card = cards_by_source.get(source_row_id)
            if not card:
                raise ValueError("SOURCE_ROW_NOT_IN_CURRENT_RELEASE")
            if payload.get("release_id") != card.get("release_id"):
                raise ValueError("RELEASE_ID_MISMATCH")
            if payload.get("review_snapshot_id") != card.get("review_snapshot_id"):
                raise ValueError("STALE_REVIEW_SNAPSHOT")
            candidates = {candidate["l3_id"] for candidate in card.get("review_candidates", [])[:2]}
            selected_l3_id = payload.get("selected_l3_id")
            if selected_l3_id not in candidates:
                raise ValueError("SELECTED_L3_NOT_CURRENT_CANDIDATE")
            row = {
                **base,
                "status": "VALID",
                "schema": SCHEMA,
                "release_id": payload["release_id"],
                "review_snapshot_id": payload["review_snapshot_id"],
                "l4_id": card["l4_id"],
                "source_row_id": source_row_id,
                "current_l3_id": card["primary_l3_id"],
                "selected_l3_id": selected_l3_id,
                "selected_rank": payload.get("selected_rank"),
                "candidate_1_l3_id": card["review_candidates"][0]["l3_id"],
                "candidate_1_em_score": card["review_candidates"][0]["em_score"],
                "candidate_2_l3_id": card["review_candidates"][1]["l3_id"],
                "candidate_2_em_score": card["review_candidates"][1]["em_score"],
                "automatic_reassignment_authorised": False,
            }
            valid_rows.append(row)
            audit_rows.append(row)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            audit_rows.append({**base, "status": "REJECTED", "reason": str(error)})

    latest_by_reviewer_card: dict[tuple[str, str, str], dict] = {}
    for row in valid_rows:
        key = (row["review_snapshot_id"], row["source_row_id"], row["reviewer"] or "")
        if key not in latest_by_reviewer_card or row["created_at"] > latest_by_reviewer_card[key]["created_at"]:
            latest_by_reviewer_card[key] = row
    effective_votes = sorted(latest_by_reviewer_card.values(), key=lambda row: (row["source_row_id"], row["reviewer"] or ""))

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in effective_votes:
        grouped[row["source_row_id"]].append(row)
    recommendations = []
    for source_row_id, rows in sorted(grouped.items()):
        counts = Counter(row["selected_l3_id"] for row in rows)
        ordered = counts.most_common()
        winner, winner_votes = ordered[0]
        tied = len(ordered) > 1 and ordered[1][1] == winner_votes
        share = winner_votes / len(rows)
        eligible = len(rows) >= args.min_reviewers and not tied and share > 0.5
        recommendations.append({
            "source_row_id": source_row_id,
            "l4_id": rows[0]["l4_id"],
            "current_l3_id": rows[0]["current_l3_id"],
            "recommended_l3_id": winner,
            "unique_reviewers": len(rows),
            "winner_votes": winner_votes,
            "winner_share": round(share, 6),
            "vote_counts": dict(sorted(counts.items())),
            "minimum_reviewers": args.min_reviewers,
            "majority_eligible": eligible,
            "proposed_change": eligible and winner != rows[0]["current_l3_id"],
            "application_status": "NOT_APPLIED_REQUIRES_EXPLICIT_USER_INSTRUCTION",
        })

    daily: dict[str, dict] = {}
    for row in valid_rows:
        day = iso_date(row["created_at"])
        entry = daily.setdefault(day, {"submitted_votes": 0, "reviewers": set(), "cards": set(), "selected_l3": Counter()})
        entry["submitted_votes"] += 1
        entry["reviewers"].add(row["reviewer"])
        entry["cards"].add(row["source_row_id"])
        entry["selected_l3"][row["selected_l3_id"]] += 1
    daily_rows = [{
        "date": day,
        "submitted_votes": value["submitted_votes"],
        "unique_reviewers": len(value["reviewers"]),
        "cards_reviewed": len(value["cards"]),
        "selected_l3_counts": dict(sorted(value["selected_l3"].items())),
    } for day, value in sorted(daily.items())]

    generated_at = max(
        (row.get("updated_at") or row.get("created_at") or "" for row in audit_rows),
        default="",
    ) or None
    summary = {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "source": "GitHub Issues",
        "automatic_reassignment": False,
        "application_policy": "Explicit user instruction is required before any taxonomy reassignment",
        "issue_records_with_marker": len(audit_rows),
        "valid_vote_issues": len(valid_rows),
        "rejected_vote_issues": sum(row["status"] == "REJECTED" for row in audit_rows),
        "effective_unique_reviewer_card_votes": len(effective_votes),
        "cards_reviewed": len(grouped),
        "majority_eligible_cards": sum(row["majority_eligible"] for row in recommendations),
        "proposed_changes": sum(row["proposed_change"] for row in recommendations),
        "daily": daily_rows,
    }

    write_jsonl(args.output_dir / "issue_vote_audit.jsonl", audit_rows)
    write_jsonl(args.output_dir / "effective_votes.jsonl", effective_votes)
    write_json(args.output_dir / "summary.json", summary)
    write_json(args.output_dir / "majority_recommendations.json", {
        "generated_at": generated_at,
        "automatic_reassignment": False,
        "recommendations": recommendations,
    })
    with (args.output_dir / "majority_recommendations.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = [
            "source_row_id", "l4_id", "current_l3_id", "recommended_l3_id", "unique_reviewers",
            "winner_votes", "winner_share", "minimum_reviewers", "majority_eligible", "proposed_change",
            "application_status", "vote_counts",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in recommendations:
            writer.writerow({**row, "vote_counts": json.dumps(row["vote_counts"], ensure_ascii=False, sort_keys=True)})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
