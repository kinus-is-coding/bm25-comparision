"""
video_retrieval_benchmark.py
-----------------------------
Prototype benchmark comparing:
  1. Elasticsearch BM25           — exact keyword retrieval on OCR+ASR
  2. BGE-M3 raw                   — semantic retrieval on OCR+ASR
  3. BGE-M3 + VLM Context         — semantic retrieval on VLM caption + OCR + ASR

Research question:
  Does BGE-M3 with VLM Contextual Retrieval outperform Elasticsearch BM25
  for video OCR/ASR retrieval when queries are semantic descriptions
  rather than exact keyword matches?

Pipeline (BGE-M3 + VLM Context):
  Video segment (OCR + ASR + keyframe VLM caption)
    → make_vlm_contextual_text()
    → BGE-M3 embedding
    → cosine similarity ranking

Run:
    python scripts/video_retrieval_benchmark.py

Notes:
- BGE-M3 requires: pip install FlagEmbedding
- Elasticsearch must be running for the BM25 leg; skipped gracefully if not.
- To replace mock VLM with a real model: swap mock_vlm_caption() — signature unchanged.
"""

from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ── Optional dependencies ────────────────────────────────────────────────────

try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False

try:
    from FlagEmbedding import BGEM3FlagModel
    BGE_AVAILABLE = True
except ImportError:
    BGE_AVAILABLE = False

# ── Constants ────────────────────────────────────────────────────────────────

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark_dataset.json")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
TOP_K = 5

# ─────────────────────────────────────────────────────────────────────────────
# 1.  VLM CONTEXTUAL ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────

def mock_vlm_caption(ocr: str, asr: str, candidate: Optional[dict] = None) -> str:
    """
    Mock VLM caption generator.

    In production this would call a Vision-Language Model (e.g. GPT-4o,
    LLaVA, Gemini) on the video keyframe to produce a visual description.

    Priority order:
      1. Use the pre-stored vlm_caption from the dataset (most realistic).
      2. Fall back to a rule-based description from OCR + ASR text.

    To replace with a real VLM API:
        def real_vlm_caption(frame_path: str) -> str:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": frame_path}},
                    {"type": "text", "text": "Describe this video frame in one sentence."}
                ]}]
            )
            return response.choices[0].message.content.strip()
    """
    if candidate and candidate.get("vlm_caption"):
        return candidate["vlm_caption"]
    # Rule-based fallback
    return f"A video frame showing: {ocr}."


# ─────────────────────────────────────────────────────────────────────────────
# 2.  TEXT PREPARATION
# ─────────────────────────────────────────────────────────────────────────────

def make_chunk_text(ocr: str, asr: str) -> str:
    """Raw OCR + ASR — used by BM25 index and raw BGE-M3."""
    return f"{ocr} {asr}".strip()


def make_vlm_contextual_text(candidate: dict) -> str:
    """
    VLM caption + OCR + ASR — used by BGE-M3 + VLM Context.

    The VLM caption is placed first so the embedding model sees
    the visual description before the noisy OCR/ASR tokens.
    """
    vlm = mock_vlm_caption(candidate["ocr"], candidate["asr"], candidate)
    return f"{vlm} {candidate['ocr']} {candidate['asr']}".strip()


# ─────────────────────────────────────────────────────────────────────────────
# 3.  ELASTICSEARCH BM25 RETRIEVAL
# ─────────────────────────────────────────────────────────────────────────────

def _es_client() -> Optional["Elasticsearch"]:
    if not ES_AVAILABLE:
        return None
    try:
        es = Elasticsearch(ES_URL, request_timeout=5)
        return es if es.ping() else None
    except Exception:
        return None


def _es_index_candidates(es: "Elasticsearch", candidates: List[dict]) -> None:
    """Index all candidates into a temporary ES index for this query."""
    idx = "benchmark_tmp"
    if es.indices.exists(index=idx):
        es.indices.delete(index=idx)
    es.indices.create(
        index=idx,
        body={
            "settings": {
                "analysis": {
                    "analyzer": {
                        "chunk_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"],
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "chunk_text": {"type": "text", "analyzer": "chunk_analyzer"}
                }
            },
        },
    )
    for i, c in enumerate(candidates):
        es.index(
            index=idx,
            id=str(i),
            body={"chunk_text": make_chunk_text(c["ocr"], c["asr"])},
            refresh=True,
        )


def retrieve_bm25(
    es: "Elasticsearch",
    query: str,
    candidates: List[dict],
    top_k: int = TOP_K,
) -> List[Tuple[int, float]]:
    """Returns [(candidate_idx, bm25_score), ...] descending."""
    _es_index_candidates(es, candidates)
    res = es.search(
        index="benchmark_tmp",
        body={
            "size": top_k,
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["chunk_text"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
        },
    )
    ranked: List[Tuple[int, float]] = [
        (int(h["_id"]), float(h["_score"])) for h in res["hits"]["hits"]
    ]
    # Append unscored candidates at the bottom
    ranked_ids = {r[0] for r in ranked}
    for i in range(len(candidates)):
        if i not in ranked_ids:
            ranked.append((i, 0.0))
    return ranked


# ─────────────────────────────────────────────────────────────────────────────
# 4.  BGE-M3 SEMANTIC RETRIEVAL
# ─────────────────────────────────────────────────────────────────────────────

_bge_model: Optional["BGEM3FlagModel"] = None


def _get_bge_model() -> Optional["BGEM3FlagModel"]:
    global _bge_model
    if not BGE_AVAILABLE:
        return None
    if _bge_model is None:
        print("  [BGE-M3] Loading model (first call — may take a moment)...")
        _bge_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    return _bge_model


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def retrieve_bge_m3(
    model: "BGEM3FlagModel",
    query: str,
    candidates: List[dict],
    use_vlm_context: bool = False,
) -> List[Tuple[int, float]]:
    """
    Returns [(candidate_idx, cosine_similarity), ...] descending.
    use_vlm_context=True → embed VLM caption + OCR + ASR.
    use_vlm_context=False → embed OCR + ASR only (raw baseline).
    """
    if use_vlm_context:
        texts = [make_vlm_contextual_text(c) for c in candidates]
    else:
        texts = [make_chunk_text(c["ocr"], c["asr"]) for c in candidates]

    embeddings = model.encode([query] + texts, batch_size=12, max_length=512)["dense_vecs"]
    q_vec = embeddings[0].tolist()
    scores = [
        (i, _cosine(q_vec, embeddings[i + 1].tolist()))
        for i in range(len(candidates))
    ]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


# ─────────────────────────────────────────────────────────────────────────────
# 5.  METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_mrr(ranked: List[Tuple[int, float]], pos: int) -> float:
    for rank, (idx, _) in enumerate(ranked, 1):
        if idx == pos:
            return 1.0 / rank
    return 0.0


def compute_recall_at_k(ranked: List[Tuple[int, float]], pos: int, k: int) -> float:
    return 1.0 if pos in {idx for idx, _ in ranked[:k]} else 0.0


def compute_ndcg_at_k(ranked: List[Tuple[int, float]], pos: int, k: int) -> float:
    for rank, (idx, _) in enumerate(ranked[:k], 1):
        if idx == pos:
            return (1.0 / math.log2(rank + 1)) / (1.0 / math.log2(2))
    return 0.0


def score_ranked(ranked: List[Tuple[int, float]], pos: int) -> Dict[str, float]:
    return {
        "MRR":      compute_mrr(ranked, pos),
        "Recall@1": compute_recall_at_k(ranked, pos, 1),
        "Recall@5": compute_recall_at_k(ranked, pos, 5),
        "NDCG@5":   compute_ndcg_at_k(ranked, pos, 5),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6.  QUALITATIVE OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 70, pad: str = "    ") -> str:
    words, lines, line, length = text.split(), [], [], 0
    for w in words:
        if length + len(w) + 1 > width and line:
            lines.append(pad + " ".join(line))
            line, length = [], 0
        line.append(w)
        length += len(w) + 1
    if line:
        lines.append(pad + " ".join(line))
    return "\n".join(lines)


def _rank_of(ranked: List[Tuple[int, float]], pos: int) -> Tuple[Optional[int], float]:
    for rank, (idx, score) in enumerate(ranked, 1):
        if idx == pos:
            return rank, score
    return None, 0.0


def print_qualitative_case(
    q: dict,
    candidates: List[dict],
    pos: int,
    bm25_ranked: List[Tuple[int, float]],
    raw_ranked: List[Tuple[int, float]],
    vlm_ranked: List[Tuple[int, float]],
) -> None:
    """
    Print a detailed case block.
    Shows ground truth, then the top-1 prediction of each method with
    OCR / ASR / VLM caption / score / correct flag.
    Triggered only when methods disagree or BGE-M3+VLM fixes a BM25 mistake.
    """
    SEP = "=" * 66
    DIV = "-" * 66

    bm25_top_idx, bm25_top_score = bm25_ranked[0]
    vlm_top_idx,  vlm_top_score  = vlm_ranked[0]

    bm25_correct = bm25_top_idx == pos
    vlm_correct  = vlm_top_idx  == pos

    # Only print interesting cases
    if bm25_correct and vlm_correct and bm25_top_idx == vlm_top_idx:
        return

    gt = candidates[pos]

    print(f"\n{SEP}")
    print(f"QUERY [{q['query_id']}]: {q['query']}")
    print(SEP)

    # Ground truth
    print()
    print("GROUND TRUTH:")
    print(f"  video_id  : {gt['video_id']}")
    print(f"  timestamp : {gt['timestamp']}")
    print("  OCR:")
    print(_wrap(f'"{gt["ocr"]}"'))
    print("  ASR:")
    print(_wrap(f'"{gt["asr"]}"'))
    print("  VLM Caption:")
    print(_wrap(f'"{mock_vlm_caption(gt["ocr"], gt["asr"], gt)}"'))

    print(f"\n{DIV}")
    print("METHOD RESULTS")
    print(DIV)

    # Helper to print one method block
    def _print_method(label: str, ranked: List[Tuple[int, float]], top_idx: int, top_score: float) -> None:
        correct = top_idx == pos
        rank_no, gt_score = _rank_of(ranked, pos)
        c = candidates[top_idx]
        mark = "✅" if correct else "❌"
        print(f"\nMethod: {label}")
        print(f"  Predicted video : {c['video_id']}")
        if not correct:
            print(f"  Negative type   : {c.get('negative_type', '—')}")
        print(f"  Score           : {top_score:.4f}")
        print(f"  Correct         : {mark} {'True' if correct else 'False'}")
        print(f"  GT rank / score : #{rank_no if rank_no else '—'}  /  {gt_score:.4f}")
        print("  Predicted OCR:")
        print(_wrap(f'"{c["ocr"]}"'))
        print("  Predicted ASR:")
        print(_wrap(f'"{c["asr"]}"'))
        if label == "BGE-M3 + VLM Context":
            print("  VLM Caption used:")
            print(_wrap(f'"{mock_vlm_caption(c["ocr"], c["asr"], c)}"'))

    _print_method("BM25", bm25_ranked, bm25_top_idx, bm25_top_score)
    _print_method("BGE-M3 + VLM Context", vlm_ranked, vlm_top_idx, vlm_top_score)

    print(f"\n{DIV}")
    if vlm_correct and not bm25_correct:
        print(f"✅ BGE-M3+VLM fixed a BM25 mistake  "
              f"(BM25 → '{candidates[bm25_top_idx]['video_id']}')")
    elif bm25_correct and not vlm_correct:
        print(f"⚠️  BM25 correct, BGE-M3+VLM wrong  "
              f"(VLM → '{candidates[vlm_top_idx]['video_id']}')")
    elif not bm25_correct and not vlm_correct:
        print("❌ Both methods wrong")
    else:
        print("ℹ️  Both correct but scored differently")
    print(SEP)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  MAIN BENCHMARK LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark(dataset: dict) -> None:
    queries = dataset["queries"]

    # ── Init backends ────────────────────────────────────────────────────────
    es = _es_client()
    print("  ✅ Elasticsearch connected." if es
          else "  ⚠️  Elasticsearch unavailable — BM25 skipped.")

    bge = _get_bge_model()
    if bge:
        print("  ✅ BGE-M3 model loaded.")
    else:
        print("  ⚠️  FlagEmbedding not installed — BGE-M3 skipped.\n"
              "       pip install FlagEmbedding")

    if not es and not bge:
        print("\n  ❌ No retrieval backend available. Exiting.")
        return

    method_scores: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    type_scores:   Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    qualitative_cases = []

    print(f"\n{'─'*65}")
    print(f"  Running benchmark on {len(queries)} queries ...")
    print(f"{'─'*65}\n")

    for q in queries:
        qid          = q["query_id"]
        query_text   = q["query"]
        candidates   = q["candidates"]
        pos          = next(i for i, c in enumerate(candidates) if c["label"] == 1)
        neg_types    = [c["negative_type"] for c in candidates if c["label"] == 0]

        ranked_bm25: List[Tuple[int, float]] = []
        ranked_raw:  List[Tuple[int, float]] = []
        ranked_vlm:  List[Tuple[int, float]] = []
        m_bm25 = m_raw = m_vlm = {}

        print(f"  [{qid}] {query_text}")

        # BM25 ────────────────────────────────────────────────────────────────
        if es:
            t0 = time.perf_counter()
            ranked_bm25 = retrieve_bm25(es, query_text, candidates)
            ms = (time.perf_counter() - t0) * 1000
            m_bm25 = score_ranked(ranked_bm25, pos)
            method_scores["Elasticsearch BM25"].append(m_bm25)
            print(f"    BM25          MRR={m_bm25['MRR']:.2f}  R@1={m_bm25['Recall@1']:.0f}  "
                  f"R@5={m_bm25['Recall@5']:.0f}  NDCG@5={m_bm25['NDCG@5']:.2f}  ({ms:.0f}ms)")

        # BGE-M3 raw ──────────────────────────────────────────────────────────
        if bge:
            t0 = time.perf_counter()
            ranked_raw = retrieve_bge_m3(bge, query_text, candidates, use_vlm_context=False)
            ms = (time.perf_counter() - t0) * 1000
            m_raw = score_ranked(ranked_raw, pos)
            method_scores["BGE-M3 raw"].append(m_raw)
            print(f"    BGE-M3 raw    MRR={m_raw['MRR']:.2f}  R@1={m_raw['Recall@1']:.0f}  "
                  f"R@5={m_raw['Recall@5']:.0f}  NDCG@5={m_raw['NDCG@5']:.2f}  ({ms:.0f}ms)")

        # BGE-M3 + VLM Context ────────────────────────────────────────────────
        if bge:
            t0 = time.perf_counter()
            ranked_vlm = retrieve_bge_m3(bge, query_text, candidates, use_vlm_context=True)
            ms = (time.perf_counter() - t0) * 1000
            m_vlm = score_ranked(ranked_vlm, pos)
            method_scores["BGE-M3 + VLM Context"].append(m_vlm)
            print(f"    BGE-M3+VLM    MRR={m_vlm['MRR']:.2f}  R@1={m_vlm['Recall@1']:.0f}  "
                  f"R@5={m_vlm['Recall@5']:.0f}  NDCG@5={m_vlm['NDCG@5']:.2f}  ({ms:.0f}ms)")

        # Per-negative-type confusion accumulation ───────────────────────────
        method_map = {}
        if es:  method_map["Elasticsearch BM25"] = ranked_bm25
        if bge: method_map["BGE-M3 raw"]         = ranked_raw
        if bge: method_map["BGE-M3 + VLM Context"] = ranked_vlm

        for neg_type in set(neg_types):
            neg_idxs = [i for i, c in enumerate(candidates)
                        if c["label"] == 0 and c["negative_type"] == neg_type]
            for method_label, ranked in method_map.items():
                rank_map = {idx: rank for rank, (idx, _) in enumerate(ranked, 1)}
                pos_rank = rank_map.get(pos, len(candidates) + 1)
                confused = sum(1 for ni in neg_idxs if rank_map.get(ni, 999) < pos_rank)
                type_scores[neg_type][method_label].append(
                    confused / len(neg_idxs) if neg_idxs else 0.0
                )

        # Collect for qualitative output ──────────────────────────────────────
        bm25_r1  = m_bm25.get("Recall@1", -1) if es  else -1
        vlm_r1   = m_vlm.get("Recall@1",  -1) if bge else -1
        bm25_mrr = m_bm25.get("MRR", -1)      if es  else -1
        vlm_mrr  = m_vlm.get("MRR",  -1)      if bge else -1
        if es and bge and ((bm25_r1 == 0) or (vlm_mrr > bm25_mrr)):
            qualitative_cases.append((q, candidates, pos, ranked_bm25, ranked_raw, ranked_vlm))

        print()

    # ── Qualitative section ──────────────────────────────────────────────────
    if qualitative_cases:
        print(f"\n{'#'*66}")
        print(f"  QUALITATIVE ANALYSIS — {len(qualitative_cases)} interesting case(s)")
        print(f"  (BM25 missed rank-1  OR  BGE-M3+VLM improved MRR over BM25)")
        print(f"{'#'*66}")
        for (q, candidates, pos, rb, rr, rv) in qualitative_cases:
            print_qualitative_case(q, candidates, pos, rb, rr, rv)
    else:
        print("\n  ℹ️  No interesting cases — BM25 perfect on all queries.")

    # ── Summary ──────────────────────────────────────────────────────────────
    _print_summary(method_scores, type_scores)
    _save_results(method_scores, type_scores)


# ─────────────────────────────────────────────────────────────────────────────
# 8.  OUTPUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _avg(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _avg_m(scores: List[Dict[str, float]], metric: str) -> float:
    return _avg([s[metric] for s in scores])


def _print_summary(
    method_scores: Dict[str, List[Dict[str, float]]],
    type_scores: Dict[str, Dict[str, List[float]]],
) -> None:
    methods = list(method_scores.keys())
    metrics = ["MRR", "Recall@1", "Recall@5", "NDCG@5"]
    W, C = 26, 11

    print()
    print("=" * 72)
    print("  VIDEO RETRIEVAL BENCHMARK — SUMMARY")
    print("=" * 72)
    print(f"  {'Method':<{W}}" + "".join(f"{m:>{C}}" for m in metrics))
    print("  " + "─" * (W + C * len(metrics)))
    for method in methods:
        row = f"  {method:<{W}}" + "".join(
            f"{_avg_m(method_scores[method], m):>{C}.3f}" for m in metrics
        )
        print(row)

    print()
    print("  Negative-type confusion rate  (↓ lower = better)")
    methods_short = [m[:12] for m in methods]
    print(f"  {'Category':<35}" + "".join(f"{m:>{C}}" for m in methods_short))
    print("  " + "─" * (35 + C * len(methods)))
    for neg_type in sorted(type_scores.keys()):
        row = f"  {neg_type:<35}"
        for method in methods:
            rate = _avg(type_scores[neg_type].get(method, [0.0]))
            row += f"{rate:>{C}.2f}"
        print(row)
    print("=" * 72)


def _save_results(
    method_scores: Dict[str, List[Dict[str, float]]],
    type_scores: Dict[str, Dict[str, List[float]]],
) -> None:
    out = {
        "overall": {
            method: {m: round(_avg_m(scores, m), 4) for m in ["MRR", "Recall@1", "Recall@5", "NDCG@5"]}
            for method, scores in method_scores.items()
        },
        "per_negative_type_confusion": {
            neg_type: {method: round(_avg(vals), 4) for method, vals in methods.items()}
            for neg_type, methods in type_scores.items()
        },
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved → {os.path.abspath(out_path)}")


# ─────────────────────────────────────────────────────────────────────────────
# 9.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    path = os.path.abspath(DATASET_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Run scripts/generate_benchmark.py first."
        )
    with open(path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"\nLoaded: {path}")
    print(f"Version: {dataset['version']}   Queries: {dataset['total_queries']}\n")
    run_benchmark(dataset)


if __name__ == "__main__":
    main()
