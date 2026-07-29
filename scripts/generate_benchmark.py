"""
generate_benchmark.py
---------------------
Validates data/benchmark_dataset.json and prints a summary.
Also serves as the authoritative source-of-truth for the benchmark schema.

Run:
    python scripts/generate_benchmark.py
"""

import json
import os
from collections import Counter

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark_dataset.json")


def validate_dataset(data: dict) -> None:
    """Validate schema integrity and print a summary report."""
    queries = data["queries"]
    taxonomy = set(data["negative_type_taxonomy"])

    total_positives = 0
    total_negatives = 0
    neg_type_counter: Counter = Counter()
    errors = []

    for q in queries:
        qid = q["query_id"]
        positives = [c for c in q["candidates"] if c["label"] == 1]
        negatives = [c for c in q["candidates"] if c["label"] == 0]

        if len(positives) != 1:
            errors.append(f"{qid}: expected exactly 1 positive, found {len(positives)}")

        if len(negatives) < 3:
            errors.append(f"{qid}: expected at least 3 negatives, found {len(negatives)}")

        for neg in negatives:
            nt = neg.get("negative_type")
            if nt not in taxonomy:
                errors.append(f"{qid}: unknown negative_type '{nt}'")
            neg_type_counter[nt] += 1

            for field in ("video_id", "timestamp", "ocr", "asr"):
                if not neg.get(field):
                    errors.append(f"{qid}/{neg['video_id']}: missing field '{field}'")

        total_positives += len(positives)
        total_negatives += len(negatives)

    covered_types = set(neg_type_counter.keys())
    missing_types = taxonomy - covered_types
    if missing_types:
        errors.append(f"Missing negative types across dataset: {missing_types}")

    # ── Report ──────────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"  BENCHMARK DATASET VALIDATION — v{data['version']}")
    print("=" * 60)
    print(f"  Total queries      : {len(queries)}")
    print(f"  Total positives    : {total_positives}")
    print(f"  Total negatives    : {total_negatives}")
    print(f"  Total candidates   : {total_positives + total_negatives}")
    print()
    print("  Negative type distribution:")
    for nt in sorted(neg_type_counter):
        print(f"    {nt:<35} {neg_type_counter[nt]:>3}")
    print()

    if errors:
        print("  ❌ VALIDATION ERRORS:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  ✅ All checks passed.")
    print("=" * 60)


def main():
    path = os.path.abspath(DATASET_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validate_dataset(data)
    print(f"\nDataset loaded from: {path}")


if __name__ == "__main__":
    main()
