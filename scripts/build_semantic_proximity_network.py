#!/usr/bin/env python3
"""Build the v2.17.2 Semantic Proximity Complex Network."""

from __future__ import annotations

import json
import warnings
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.17.2"
EMBEDDINGS = ROOT / "reports/validation/v2.17.2/bge_m3_active/card_embeddings.npy"
INDEX = ROOT / "reports/validation/v2.17.2/bge_m3_active/index.json"
SPACE = RELEASE / "risk_space.json"
OUTPUT = RELEASE / "semantic_proximity_network.json"

K_NEIGHBORS = 8
MIN_SIMILARITY = 0.62
PROJECTED_K_NEIGHBORS = 10
L3_PROFILE_WEIGHT = 0.65
DIRECT_SEMANTIC_WEIGHT = 0.35
L3_AFFILIATION_FACTOR = 1.5
SEED = 42
EM_MAX_ITERATIONS = 60
EM_BETA = 18.0
EM_GRAPH_LAMBDA = 2.0
EM_SEED_WEIGHT = 5.0
EM_TOLERANCE = 1e-4


def normalize_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


def build_graph(embeddings: np.ndarray) -> tuple[nx.Graph, np.ndarray]:
    similarities = embeddings @ embeddings.T
    np.fill_diagonal(similarities, -np.inf)
    nearest = np.argpartition(
        -similarities, kth=K_NEIGHBORS - 1, axis=1
    )[:, :K_NEIGHBORS]

    graph = nx.Graph()
    graph.add_nodes_from(range(len(embeddings)))
    for source, neighbors in enumerate(nearest):
        for target in neighbors:
            similarity = float(similarities[source, target])
            if similarity < MIN_SIMILARITY:
                continue
            graph.add_edge(
                source,
                int(target),
                weight=similarity,
                distance=1.0 - similarity,
            )
    return graph, similarities


def build_l3_profile_projected_graph(
    embeddings: np.ndarray, responsibilities: np.ndarray
) -> nx.Graph:
    semantic_similarity = embeddings @ embeddings.T
    uniform_baseline = 1.0 / responsibilities.shape[1]
    excess_profile = np.maximum(responsibilities - uniform_baseline, 0.0)
    excess_profile = normalize_rows(excess_profile)
    profile_similarity = excess_profile @ excess_profile.T
    combined = (
        DIRECT_SEMANTIC_WEIGHT * semantic_similarity
        + L3_PROFILE_WEIGHT * profile_similarity
    )
    np.fill_diagonal(combined, -np.inf)
    nearest = np.argpartition(
        -combined,
        kth=PROJECTED_K_NEIGHBORS - 1,
        axis=1,
    )[:, :PROJECTED_K_NEIGHBORS]
    graph = nx.Graph()
    graph.add_nodes_from(range(len(embeddings)))
    for source, neighbors in enumerate(nearest):
        for target in neighbors:
            target = int(target)
            weight = float(combined[source, target])
            graph.add_edge(
                source,
                target,
                weight=weight,
                distance=1.0 - weight,
                semantic_similarity=float(semantic_similarity[source, target]),
                l3_profile_similarity=float(profile_similarity[source, target]),
            )
    return graph


def l3_affiliations(
    responsibilities: np.ndarray,
    family_ids: list[str],
    family_labels: dict[str, tuple[str, str]],
) -> list[list[dict]]:
    threshold = L3_AFFILIATION_FACTOR / len(family_ids)
    all_affiliations = []
    for row in responsibilities:
        ranked = np.argsort(-row)
        selected = [index for index in ranked if row[index] >= threshold]
        if not selected:
            selected = [int(ranked[0])]
        all_affiliations.append(
            [
                {
                    "l3_id": family_ids[index],
                    "label_en": family_labels[family_ids[index]][0],
                    "label_ko": family_labels[family_ids[index]][1],
                    "responsibility": round(float(row[index]), 6),
                }
                for index in selected
            ]
        )
    return all_affiliations


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - values.max(axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.maximum(exponentials.sum(axis=1, keepdims=True), 1e-12)


def graph_regularized_seeded_spherical_em(
    embeddings: np.ndarray,
    graph: nx.Graph,
    family_ids: list[str],
    points: list[dict],
) -> tuple[np.ndarray, np.ndarray, list[set[int]], dict]:
    family_index = {family_id: index for index, family_id in enumerate(family_ids)}
    seed_centroids = np.zeros((len(family_ids), embeddings.shape[1]), dtype=float)
    seed_counts = np.zeros(len(family_ids), dtype=float)
    for node, point in enumerate(points):
        family_id = point["path"]["l3_id"]
        if family_id not in family_index:
            continue
        cluster = family_index[family_id]
        seed_centroids[cluster] += embeddings[node]
        seed_counts[cluster] += 1
    if np.any(seed_counts == 0):
        missing = [family_ids[index] for index in np.flatnonzero(seed_counts == 0)]
        raise RuntimeError(f"Missing L3 seed cards: {missing}")
    seed_centroids /= seed_counts[:, None]
    seed_centroids = normalize_rows(seed_centroids)
    centroids = seed_centroids.copy()

    rows = []
    columns = []
    weights = []
    for source, target, attributes in graph.edges(data=True):
        weight = float(attributes["weight"])
        rows.extend([source, target])
        columns.extend([target, source])
        weights.extend([weight, weight])
    adjacency = csr_matrix(
        (weights, (rows, columns)),
        shape=(len(embeddings), len(embeddings)),
        dtype=float,
    )
    row_sums = np.asarray(adjacency.sum(axis=1)).ravel()
    normalized_adjacency = adjacency.multiply(
        (1.0 / np.maximum(row_sums, 1e-12))[:, None]
    ).tocsr()

    responsibilities = softmax(EM_BETA * (embeddings @ centroids.T))
    previous_assignment = responsibilities.argmax(axis=1)
    history = []
    for iteration in range(1, EM_MAX_ITERATIONS + 1):
        neighborhood = normalized_adjacency @ responsibilities
        logits = (
            EM_BETA * (embeddings @ centroids.T)
            + EM_GRAPH_LAMBDA * neighborhood
        )
        responsibilities = softmax(logits)
        weighted_sum = responsibilities.T @ embeddings
        weighted_sum += EM_SEED_WEIGHT * seed_centroids
        centroids = normalize_rows(weighted_sum)
        assignment = responsibilities.argmax(axis=1)
        change_rate = float(np.mean(assignment != previous_assignment))
        mean_similarity = float(
            np.mean(np.sum(embeddings * centroids[assignment], axis=1))
        )
        history.append(
            {
                "iteration": iteration,
                "change_rate": round(change_rate, 6),
                "mean_similarity": round(mean_similarity, 6),
            }
        )
        previous_assignment = assignment
        if iteration >= 3 and change_rate <= EM_TOLERANCE:
            break

    communities = [
        set(np.flatnonzero(assignment == cluster).tolist())
        for cluster in range(len(family_ids))
    ]
    empty = [index for index, members in enumerate(communities) if not members]
    if empty:
        raise RuntimeError(f"EM produced empty clusters: {empty}")
    diagnostics = {
        "iterations": history[-1]["iteration"],
        "final_change_rate": history[-1]["change_rate"],
        "final_mean_similarity": history[-1]["mean_similarity"],
        "history": history,
    }
    return assignment, responsibilities, communities, diagnostics


def representative_nodes(
    graph: nx.Graph, members: set[int], points: list[dict], count: int = 4
) -> list[dict]:
    ranked = sorted(
        members,
        key=lambda node: graph.degree(node, weight="weight"),
        reverse=True,
    )
    return [
        {
            "id": points[node]["id"],
            "label_en": points[node]["label_en"],
            "label_ko": points[node].get("label_ko", ""),
        }
        for node in ranked[:count]
    ]


def normalized_layout(
    graph: nx.Graph, communities: list[set[int]]
) -> dict[int, tuple[float, float]]:
    rng = np.random.default_rng(SEED)
    cluster_by_node = {
        node: cluster_id
        for cluster_id, members in enumerate(communities)
        for node in members
    }
    coarse = nx.Graph()
    coarse.add_nodes_from(range(len(communities)))
    for source, target, attributes in graph.edges(data=True):
        source_cluster = cluster_by_node[source]
        target_cluster = cluster_by_node[target]
        if source_cluster == target_cluster:
            continue
        weight = attributes["weight"]
        if coarse.has_edge(source_cluster, target_cluster):
            coarse[source_cluster][target_cluster]["weight"] += weight
        else:
            coarse.add_edge(source_cluster, target_cluster, weight=weight)
    coarse_positions = nx.spring_layout(
        coarse,
        iterations=300,
        seed=SEED,
        weight="weight",
        scale=5.0,
    )
    initial = {}
    for cluster_id, members in enumerate(communities):
        center = np.asarray(coarse_positions[cluster_id], dtype=float)
        for node in members:
            initial[node] = center + rng.normal(0.0, 0.28, size=2)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="invalid value encountered in divide",
            category=RuntimeWarning,
        )
        positions = nx.forceatlas2_layout(
            graph,
            pos=initial,
            max_iter=350,
            scaling_ratio=8.0,
            gravity=0.12,
            strong_gravity=False,
            weight="weight",
            linlog=True,
            seed=SEED,
        )
    values = np.array([positions[node] for node in graph.nodes()], dtype=float)
    low = np.percentile(values, 1.0, axis=0)
    high = np.percentile(values, 99.0, axis=0)
    span = np.maximum(high - low, 1e-12)
    scaled = np.clip(((values - low) / span) * 2.0 - 1.0, -1.0, 1.0)
    return {
        node: (float(scaled[index, 0]), float(scaled[index, 1]))
        for index, node in enumerate(graph.nodes())
    }


def dominant_released_paths(members: set[int], points: list[dict]) -> list[dict]:
    counts = Counter(points[node]["path"]["l3_id"] for node in members)
    labels = {}
    for node in members:
        path = points[node]["path"]
        labels[path["l3_id"]] = (
            path["l3_label_en"],
            path.get("l3_label_ko", ""),
        )
    dominant = []
    for l3_id, count in counts.most_common(3):
        label_en, label_ko = labels[l3_id]
        dominant.append(
            {
                "l3_id": l3_id,
                "label_en": label_en,
                "label_ko": label_ko,
                "count": count,
                "share": round(count / len(members), 4),
            }
        )
    return dominant


def main() -> None:
    embeddings = normalize_rows(np.load(EMBEDDINGS).astype(np.float64))
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    payload = json.loads(SPACE.read_text(encoding="utf-8"))
    points = payload["points"]

    l4_ids = index["l4_ids"]
    point_by_id = {point["id"]: point for point in points}
    if set(l4_ids) != set(point_by_id):
        raise RuntimeError("Embedding index and active risk-space IDs do not match")
    ordered_points = [point_by_id[risk_id] for risk_id in l4_ids]

    base_graph, _ = build_graph(embeddings)
    assignments, responsibilities, communities, em_diagnostics = (
        graph_regularized_seeded_spherical_em(
            embeddings,
            base_graph,
            index["fam_ids"],
            ordered_points,
        )
    )
    cluster_by_node = {
        node: int(assignments[node]) for node in range(len(ordered_points))
    }
    family_labels = {}
    for point in ordered_points:
        path = point["path"]
        if path["l3_id"] in index["fam_ids"]:
            family_labels[path["l3_id"]] = (
                path["l3_label_en"],
                path.get("l3_label_ko", ""),
            )
    affiliations = l3_affiliations(
        responsibilities,
        index["fam_ids"],
        family_labels,
    )
    graph = build_l3_profile_projected_graph(embeddings, responsibilities)
    positions = normalized_layout(graph, communities)
    clusters = []
    for cluster_id, members in enumerate(communities):
        family_id = index["fam_ids"][cluster_id]
        label_en, label_ko = family_labels[family_id]
        centroid = np.mean([positions[node] for node in members], axis=0)
        clusters.append(
            {
                "id": cluster_id,
                "seed_l3_id": family_id,
                "label_en": label_en,
                "label_ko": label_ko,
                "size": len(members),
                "x": round(float(centroid[0]), 5),
                "y": round(float(centroid[1]), 5),
                "dominant_released_paths": dominant_released_paths(
                    members, ordered_points
                ),
                "representatives": representative_nodes(
                    graph, members, ordered_points
                ),
            }
        )

    nodes = []
    for node, point in enumerate(ordered_points):
        x, y = positions[node]
        nodes.append(
            {
                "id": point["id"],
                "label_en": point["label_en"],
                "label_ko": point.get("label_ko", ""),
                "cluster": cluster_by_node[node],
                "x": round(x, 5),
                "y": round(y, 5),
                "degree": int(graph.degree(node)),
                "strength": round(float(graph.degree(node, weight="weight")), 5),
                "hold": bool(point.get("decision_required")),
                "l3_affiliation_count": len(affiliations[node]),
                "l3_affiliations": affiliations[node],
            }
        )

    edges = [
        [
            int(source),
            int(target),
            round(float(attributes["weight"]), 5),
            round(float(attributes["distance"]), 5),
            round(float(attributes["semantic_similarity"]), 5),
            round(float(attributes["l3_profile_similarity"]), 5),
        ]
        for source, target, attributes in graph.edges(data=True)
    ]

    output = {
        "metadata": {
            "title": "Semantic Proximity Complex Network",
            "release": "v2.17.2",
            "embedding_model": "BAAI/bge-m3",
            "active_cards": len(nodes),
            "direct_semantic_distance": "1 - cosine_similarity",
            "edge_distance": "1 - projected_edge_weight",
            "base_knn_k": K_NEIGHBORS,
            "base_minimum_similarity": MIN_SIMILARITY,
            "projected_knn_k": PROJECTED_K_NEIGHBORS,
            "community_method": "Graph-Regularized Seeded Spherical EM",
            "em_beta": EM_BETA,
            "em_graph_lambda": EM_GRAPH_LAMBDA,
            "em_seed_weight": EM_SEED_WEIGHT,
            "em_diagnostics": em_diagnostics,
            "l3_affiliation_threshold": round(
                L3_AFFILIATION_FACTOR / len(index["fam_ids"]), 5
            ),
            "projected_edge_weight": {
                "l3_profile_similarity": L3_PROFILE_WEIGHT,
                "direct_semantic_similarity": DIRECT_SEMANTIC_WEIGHT,
            },
            "layout": "ForceAtlas2",
            "seed": SEED,
            "edge_count": len(edges),
            "cluster_count": len(clusters),
        },
        "clusters": clusters,
        "nodes": nodes,
        "edges": edges,
    }
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(ROOT)),
                "nodes": len(nodes),
                "edges": len(edges),
                "clusters": [
                    {"label": cluster["label_en"], "size": cluster["size"]}
                    for cluster in clusters
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
