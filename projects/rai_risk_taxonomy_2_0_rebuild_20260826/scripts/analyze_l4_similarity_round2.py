#!/usr/bin/env python3
"""Extract the most similar L4 pairs from the round-two reviewed release."""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "05_human_review_round2"
MODEL = Path(
    os.environ.get(
        "RAI_BGE_M3_MODEL",
        Path.home()
        / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181",
    )
)
DOMAINS = ("General", "Agentic", "Physical")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of highest-similarity non-self pairs to export (default: 10)",
    )
    parser.add_argument(
        "--domain",
        choices=("All", *DOMAINS),
        default="All",
        help="Limit comparison to one L1 domain (default: All)",
    )
    parser.add_argument(
        "--same-l3-only",
        action="store_true",
        help="Rank only pairs assigned to the same L3 category",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(texts: list[str], tokenizer, model, device: torch.device, batch_size: int = 8) -> np.ndarray:
    batches: list[np.ndarray] = []
    for start in range(0, len(texts), batch_size):
        tokens = tokenizer(
            texts[start : start + batch_size],
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors="pt",
        )
        tokens = {key: value.to(device) for key, value in tokens.items()}
        with torch.inference_mode():
            hidden = model(**tokens).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(hidden, p=2, dim=1)
        batches.append(hidden.detach().cpu().numpy().astype("float32"))
    return np.vstack(batches)


def main() -> None:
    args = parse_args()
    if args.top_k < 1:
        raise ValueError("--top-k must be a positive integer")

    input_paths = {
        domain: INPUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"
        for domain in DOMAINS
    }
    all_cards: list[dict[str, str]] = []
    for domain, input_path in input_paths.items():
        for row in read_csv(input_path):
            row["Domain"] = domain
            all_cards.append(row)
    summary = json.loads((INPUT / "Human_Review_Round2_Summary.json").read_text(encoding="utf-8"))
    if len(all_cards) != summary["output_rows"]:
        raise ValueError(f"Summary expects {summary['output_rows']} reviewed L4 cards, found {len(all_cards)}")
    if len({row["L4_ID"] for row in all_cards}) != len(all_cards):
        raise ValueError("L4 IDs are not unique")
    cards = all_cards if args.domain == "All" else [row for row in all_cards if row["Domain"] == args.domain]

    ko_texts = [f'{row["L4_Title_ko"]}. {row["L4_Description_ko"]}' for row in cards]
    en_texts = [f'{row["L4_Title_en"]}. {row["L4_Description_en"]}' for row in cards]
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    model = AutoModel.from_pretrained(MODEL, local_files_only=True, use_safetensors=False).to(device)
    model.eval()
    ko_embeddings = encode(ko_texts, tokenizer, model, device)
    en_embeddings = encode(en_texts, tokenizer, model, device)

    similarity_ko = ko_embeddings @ ko_embeddings.T
    similarity_en = en_embeddings @ en_embeddings.T
    bilingual_similarity = 0.5 * (similarity_ko + similarity_en)
    left_indices, right_indices = np.triu_indices(len(cards), k=1)
    pair_scores = bilingual_similarity[left_indices, right_indices]
    if args.same_l3_only:
        same_l3_mask = np.fromiter(
            (cards[left]["L3_ID"] == cards[right]["L3_ID"] for left, right in zip(left_indices, right_indices)),
            dtype=bool,
            count=len(left_indices),
        )
        left_indices = left_indices[same_l3_mask]
        right_indices = right_indices[same_l3_mask]
        pair_scores = pair_scores[same_l3_mask]
    if args.top_k > len(pair_scores):
        raise ValueError(f"--top-k {args.top_k} exceeds {len(pair_scores)} candidate pairs")
    top_positions = np.argpartition(pair_scores, -args.top_k)[-args.top_k:]
    top_positions = top_positions[np.argsort(pair_scores[top_positions])[::-1]]

    output_rows: list[dict[str, object]] = []
    seen_pairs: set[frozenset[str]] = set()
    for rank, position in enumerate(top_positions, 1):
        left_index = int(left_indices[position])
        right_index = int(right_indices[position])
        left = cards[left_index]
        right = cards[right_index]
        pair = frozenset((left["L4_ID"], right["L4_ID"]))
        if len(pair) != 2 or pair in seen_pairs:
            raise ValueError("Self-pair or reverse duplicate reached the ranked output")
        seen_pairs.add(pair)
        output_rows.append(
            {
                "Rank": rank,
                "Left_L4_ID": left["L4_ID"],
                "Left_Domain": left["Domain"],
                "Left_L3_ID": left["L3_ID"],
                "Left_Title_ko": left["L4_Title_ko"],
                "Left_Description_ko": left["L4_Description_ko"],
                "Left_Title_en": left["L4_Title_en"],
                "Left_Description_en": left["L4_Description_en"],
                "Right_L4_ID": right["L4_ID"],
                "Right_Domain": right["Domain"],
                "Right_L3_ID": right["L3_ID"],
                "Right_Title_ko": right["L4_Title_ko"],
                "Right_Description_ko": right["L4_Description_ko"],
                "Right_Title_en": right["L4_Title_en"],
                "Right_Description_en": right["L4_Description_en"],
                "Similarity_ko": round(float(similarity_ko[left_index, right_index]), 6),
                "Similarity_en": round(float(similarity_en[left_index, right_index]), 6),
                "Bilingual_Similarity": round(float(bilingual_similarity[left_index, right_index]), 6),
                "Same_L1": left["L1_ID"] == right["L1_ID"],
                "Same_L3": left["L3_ID"] == right["L3_ID"],
            }
        )

    scope_parts = ["L4"]
    if args.domain != "All":
        scope_parts.append(args.domain)
    scope_parts.append(f"Top{args.top_k}")
    if args.same_l3_only:
        scope_parts.append("SameL3")
    output_stem = "_".join(scope_parts) + "_Similar_Pairs"
    output_path = INPUT / f"{output_stem}.csv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    metadata = {
        "status": "PASS",
        "all_input_cards": len(all_cards),
        "comparison_cards": len(cards),
        "candidate_pairs": len(pair_scores),
        "top_k": args.top_k,
        "domain": args.domain,
        "same_l3_only": args.same_l3_only,
        "text": "title plus definition, encoded separately in Korean and English",
        "score": "mean of Korean and English cosine similarity",
        "model": "BAAI/bge-m3",
        "model_snapshot": MODEL.name,
        "input_sha256": {
            input_path.name: sha256(input_path)
            for input_path in input_paths.values()
        },
        "round2_summary_sha256": sha256(INPUT / "Human_Review_Round2_Summary.json"),
        "final_qa_manifest_sha256": summary[
            "final_terminology_l3_qa_manifest_sha256"
        ],
        "pooling": "CLS",
        "normalised": True,
        "self_pairs_excluded": True,
        "reverse_duplicates_excluded": True,
        "output": output_path.name,
    }
    (INPUT / f"{output_stem}_Metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"metadata": metadata, "pairs": output_rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
