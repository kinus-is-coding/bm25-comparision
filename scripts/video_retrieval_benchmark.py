"""
video_retrieval_benchmark.py
-----------------------------
Prototype benchmark comparing:
  1. Elasticsearch BM25           — exact keyword retrieval on OCR+ASR
  2. BGE-M3 raw                   — semantic retrieval on OCR+ASR only
  3. BGE-M3 + VLM-structured      — semantic retrieval with section markers
  4. BGE-M3 + VLM-late-fusion     — multi-vector weighted fusion

Run:
    python scripts/video_retrieval_benchmark.py
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

# ── VLM CAPTION ──────────────────────────────────────────────────────────────

def mock_vlm_caption(ocr: str, asr: str, candidate: Optional[dict] = None) -> str:
    if candidate and candidate.get("vlm_caption"):
        return candidate["vlm_caption"]
    return f"A video frame showing: {ocr}."


# ── TEXT PREPARATION ─────────────────────────────────────────────────────────

def make_chunk_text(ocr: str, asr: str) -> str:
    return f"{ocr} {asr}".strip()


def make_vlm_contextual_text(candidate: dict, style: str = "structured") -> str:
    vlm = mock_vlm_caption(candidate["ocr"], candidate["asr"], candidate)

    if style == "concat":
        return f"{vlm} {candidate['ocr']} {candidate['asr']}".strip()
    elif style == "structured":
        return f"[VISUAL] {vlm}\n[OCR] {candidate['ocr']}\n[ASR] {candidate['asr']}"
    elif style == "instruction":
        return f"Visual description: {vlm}\nText on screen: {candidate['ocr']}\nSpoken: {candidate['asr']}"
    elif style == "weighted_prefix":
        return f"IMPORTANT - Scene: {vlm}\nSecondary - OCR: {candidate['ocr']}\nSecondary - ASR: {candidate['asr']}"
    else:
        raise ValueError(f"Unknown style: {style}")


# ── ELASTICSEARCH BM25 ───────────────────────────────────────────────────────

def _es_client() -> Optional["Elasticsearch"]:
    if not ES_AVAILABLE:
        return None
    try:
        es = Elasticsearch(ES_URL, request_timeout=5)
        return es if es.ping() else None
    except Exception:
        return None


def _es_index_candidates(es: "Elasticsearch", candidates: List[dict]) -> None:
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
        es.index(index=idx, id=str(i), body={"chunk_text": make_chunk_text(c["ocr"], c["asr"])}, refresh=True)


def retrieve_bm25(es: "Elasticsearch", query: str, candidates: List[dict], top_k: int = TOP_K) -> List[Tuple[int, float]]:
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
    ranked = [(int(h["_id"]), float(h["_score"])) for h in res["hits"]["hits"]]
    ranked_ids = {r[0] for r in ranked}
    for i in range(len(candidates)):
        if i not in ranked_ids:
            ranked.append((i, 0.0))
    return ranked


# ── BGE-M3 ───────────────────────────────────────────────────────────────────

_bge_model: Optional["BGEM3FlagModel"] = None


def _get_bge_model() -> Optional["BGEM3FlagModel"]:
    global _bge_model
    if not BGE_AVAILABLE:
        return None
    if _bge_model is None:
        print("  [BGE-M3] Loading model...")
        _bge_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    return _bge_model


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def retrieve_bge_m3_single(model, query: str, candidates: List[dict], use_vlm: bool = False, style: str = "structured") -> List[Tuple[int, float]]:
    """Single-vector embedding (concat or structured)."""
    if use_vlm:
        texts = [make_vlm_contextual_text(c, style=style) for c in candidates]
    else:
        texts = [make_chunk_text(c["ocr"], c["asr"]) for c in candidates]

    embeddings = model.encode([query] + texts, batch_size=12, max_length=512)["dense_vecs"]
    q_vec = embeddings[0].tolist()
    scores = [(i, _cosine(q_vec, embeddings[i + 1].tolist())) for i in range(len(candidates))]
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def retrieve_bge_m3_late_fusion(model, query: str, candidates: List[dict], 
                                 w_vlm: float = 0, w_ocr: float = 0.6, w_asr: float = 0.4) -> List[Tuple[int, float]]:
    """Late fusion: embed VLM, OCR, ASR separately then weighted combine."""
    q_emb = model.encode([query], batch_size=1, max_length=512)["dense_vecs"][0]

    scores = []
    for i, c in enumerate(candidates):
        vlm_text = mock_vlm_caption(c["ocr"], c["asr"], c)
        ocr_text = c["ocr"]
        asr_text = c["asr"]

        embs = model.encode([vlm_text, ocr_text, asr_text], batch_size=3, max_length=512)["dense_vecs"]

        sim_vlm = _cosine(q_emb.tolist(), embs[0].tolist())
        sim_ocr = _cosine(q_emb.tolist(), embs[1].tolist())
        sim_asr = _cosine(q_emb.tolist(), embs[2].tolist())

        score = w_vlm * sim_vlm + w_ocr * sim_ocr + w_asr * sim_asr
        scores.append((i, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def retrieve_bge_m3_sparse_ocr_asr_dense_vlm(model, query: str, candidates: List[dict],
                                               sparse_weight: float = 0.3, dense_weight: float = 0.7) -> List[Tuple[int, float]]:
    """
    Hybrid: Sparse trên OCR+ASR (exact keyword match) 
            + Dense trên [VISUAL]+[OCR]+[ASR] (semantic).

    Sparse giúp exact match keywords (OCR+ASR rõ ràng)
    Dense giúp semantic understanding (VLM+OCR+ASR đầy đủ context)
    """
    # Dense: encode VLM+OCR+ASR structured
    dense_texts = [make_vlm_contextual_text(c, style="structured") for c in candidates]
    q_dense_output = model.encode([query], batch_size=1, max_length=512, return_dense=True)
    c_dense_output = model.encode(dense_texts, batch_size=12, max_length=512, return_dense=True)

    q_dense = q_dense_output["dense_vecs"][0]

    # Sparse: encode OCR+ASR only
    sparse_texts = [make_chunk_text(c["ocr"], c["asr"]) for c in candidates]
    q_sparse_output = model.encode([query], batch_size=1, max_length=512, return_sparse=True)
    c_sparse_output = model.encode(sparse_texts, batch_size=12, max_length=512, return_sparse=True)

    q_sparse = q_sparse_output["lexical_weights"][0]

    scores = []
    for i in range(len(candidates)):
        # Dense score (VLM+OCR+ASR)
        c_dense = c_dense_output["dense_vecs"][i]
        sim_dense = _cosine(q_dense.tolist(), c_dense.tolist())

        # Sparse score (OCR+ASR only)
        c_sparse = c_sparse_output["lexical_weights"][i]
        sim_sparse = 0.0
        common_tokens = set(q_sparse.keys()) & set(c_sparse.keys())
        for tok in common_tokens:
            sim_sparse += min(q_sparse[tok], c_sparse[tok])

        if len(common_tokens) > 0:
            q_norm = sum(abs(w) for w in q_sparse.values())
            if q_norm > 0:
                sim_sparse = sim_sparse / q_norm

        # Combine
        score = dense_weight * sim_dense + sparse_weight * sim_sparse
        scores.append((i, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores

# ── METRICS ──────────────────────────────────────────────────────────────────

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
        "MRR": compute_mrr(ranked, pos),
        "Recall@1": compute_recall_at_k(ranked, pos, 1),
        "Recall@5": compute_recall_at_k(ranked, pos, 5),
        "Recall@10": compute_recall_at_k(ranked, pos, 10),
        "NDCG@5": compute_ndcg_at_k(ranked, pos, 5),
        "NDCG@10": compute_ndcg_at_k(ranked, pos, 10),
    }


# ── QUALITATIVE OUTPUT ───────────────────────────────────────────────────────

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
    structured_ranked: List[Tuple[int, float]],
    late_fusion_ranked: List[Tuple[int, float]],
    sparse_dense_ranked: List[Tuple[int, float]],
) -> None:
    """Print detailed comparison of all methods."""
    SEP = "=" * 70
    DIV = "-" * 70

    bm25_top_idx = bm25_ranked[0][0] if bm25_ranked else -1
    raw_top_idx = raw_ranked[0][0] if raw_ranked else -1
    struct_top_idx = structured_ranked[0][0] if structured_ranked else -1
    late_fusion_top_idx = late_fusion_ranked[0][0] if late_fusion_ranked else -1
    sparse_dense_top_idx = sparse_dense_ranked[0][0] if sparse_dense_ranked else -1

    bm25_correct = bm25_top_idx == pos
    raw_correct = raw_top_idx == pos
    struct_correct = struct_top_idx == pos
    late_fusion_correct = late_fusion_top_idx == pos
    sparse_dense_correct = sparse_dense_top_idx == pos

    # Only print if there's disagreement
    all_correct = [bm25_correct, raw_correct, struct_correct, late_fusion_correct, sparse_dense_correct]
    all_top = [bm25_top_idx, raw_top_idx, struct_top_idx, late_fusion_top_idx, sparse_dense_top_idx]
    if all(all_correct) and len(set(all_top)) == 1:
        return

    gt = candidates[pos]

    print(f"\n{SEP}")
    print(f"QUERY [{q['query_id']}]: {q['query']}")
    print(f"Pool size: {len(candidates)} candidates")
    print(SEP)

    print("\nGROUND TRUTH:")
    print(f"  video_id  : {gt['video_id']}")
    print(f"  timestamp : {gt['timestamp']}")
    print("  OCR:", _wrap(f'"{gt["ocr"]}"'))
    print("  ASR:", _wrap(f'"{gt["asr"]}"'))
    print("  VLM:", _wrap(f'"{mock_vlm_caption(gt["ocr"], gt["asr"], gt)}"'))

    print(f"\n{DIV}")
    print("METHOD RESULTS")
    print(DIV)

    methods = [
        ("BM25", bm25_ranked, bm25_top_idx),
        ("BGE-M3 raw (OCR+ASR)", raw_ranked, raw_top_idx),
        ("BGE-M3 + VLM-structured", structured_ranked, struct_top_idx),
        ("BGE-M3 + LateFusion", late_fusion_ranked, late_fusion_top_idx),
        ("BGE-M3 + SparseOCR-DenseVLM", sparse_dense_ranked, sparse_dense_top_idx),
    ]

    for label, ranked, top_idx in methods:
        if not ranked:
            continue
        correct = top_idx == pos
        rank_no, gt_score = _rank_of(ranked, pos)
        c = candidates[top_idx]
        mark = "✅" if correct else "❌"
        print(f"\n  {label}")
        print(f"    Top-1: {c['video_id']}")
        print(f"    Correct: {mark} | GT rank: #{rank_no if rank_no else '—'} | GT score: {gt_score:.4f}")
        print(f"    OCR: {_wrap(c['ocr'])}")

    print(f"\n{DIV}")
    # Summary
    winners = [name for name, _, top in methods if top == pos]
    if winners:
        print(f"✅ Correct: {', '.join(winners)}")
    else:
        print("❌ All methods wrong")
    print(SEP)


# ── MAIN BENCHMARK LOOP ──────────────────────────────────────────────────────

def run_benchmark(dataset: dict) -> None:
    queries = dataset["queries"]

    es = _es_client()
    print("  ✅ Elasticsearch connected." if es else "  ⚠️  Elasticsearch unavailable — BM25 skipped.")

    bge = _get_bge_model()
    if bge:
        print("  ✅ BGE-M3 model loaded.")
    else:
        print("  ⚠️  FlagEmbedding not installed — BGE-M3 skipped.\n       pip install FlagEmbedding")

    if not es and not bge:
        print("\n  ❌ No retrieval backend available. Exiting.")
        return

    method_scores: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    type_scores: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    qualitative_cases = []

    print(f"\n{'─'*65}")
    print(f"  Running benchmark on {len(queries)} queries ...")
    print(f"{'─'*65}\n")

    for q in queries:
        qid = q["query_id"]
        query_text = q["query"]
        candidates = q["candidates"]
        pos = next(i for i, c in enumerate(candidates) if c["label"] == 1)
        neg_types = [c["negative_type"] for c in candidates if c["label"] == 0]

        print(f"  [{qid}] {query_text} (pool: {len(candidates)})")

        # 1. BM25
        ranked_bm25 = []
        m_bm25 = {}
        if es:
            t0 = time.perf_counter()
            ranked_bm25 = retrieve_bm25(es, query_text, candidates)
            ms = (time.perf_counter() - t0) * 1000
            m_bm25 = score_ranked(ranked_bm25, pos)
            method_scores["Elasticsearch BM25"].append(m_bm25)
            print(f"    BM25                  MRR={m_bm25['MRR']:.3f}  R@1={m_bm25['Recall@1']:.0f}  R@5={m_bm25['Recall@5']:.0f}  ({ms:.0f}ms)")

        # 2. BGE-M3 raw (OCR+ASR only)
        ranked_raw = []
        m_raw = {}
        if bge:
            t0 = time.perf_counter()
            ranked_raw = retrieve_bge_m3_single(bge, query_text, candidates, use_vlm=False)
            ms = (time.perf_counter() - t0) * 1000
            m_raw = score_ranked(ranked_raw, pos)
            method_scores["BGE-M3 raw"].append(m_raw)
            print(f"    BGE-M3 raw            MRR={m_raw['MRR']:.3f}  R@1={m_raw['Recall@1']:.0f}  R@5={m_raw['Recall@5']:.0f}  ({ms:.0f}ms)")

        # 3. BGE-M3 + VLM-structured (chỉ giữ style tốt nhất)
        style_results = {}
        if bge:
            t0 = time.perf_counter()
            ranked = retrieve_bge_m3_single(bge, query_text, candidates, use_vlm=True, style="structured")
            ms = (time.perf_counter() - t0) * 1000
            m = score_ranked(ranked, pos)
            label = "BGE-M3+VLM-structured"
            method_scores[label].append(m)
            style_results["structured"] = (ranked, m)
            print(f"    {label:20s}  MRR={m['MRR']:.3f}  R@1={m['Recall@1']:.0f}  R@5={m['Recall@5']:.0f}  ({ms:.0f}ms)")

        # 4. BGE-M3 + Late Fusion (multi-vector)
        ranked_fusion = []
        m_fusion = {}
        if bge:
            t0 = time.perf_counter()
            ranked_fusion = retrieve_bge_m3_late_fusion(bge, query_text, candidates)
            ms = (time.perf_counter() - t0) * 1000
            m_fusion = score_ranked(ranked_fusion, pos)
            method_scores["BGE-M3+LateFusion"].append(m_fusion)
            print(f"    BGE-M3+LateFusion     MRR={m_fusion['MRR']:.3f}  R@1={m_fusion['Recall@1']:.0f}  R@5={m_fusion['Recall@5']:.0f}  ({ms:.0f}ms)")

        # 5. BGE-M3 Sparse-OCR-ASR + Dense-VLM (ý tưởng mới)
        ranked_sparse_dense = []
        m_sparse_dense = {}
        if bge:
            t0 = time.perf_counter()
            ranked_sparse_dense = retrieve_bge_m3_sparse_ocr_asr_dense_vlm(bge, query_text, candidates)
            ms = (time.perf_counter() - t0) * 1000
            m_sparse_dense = score_ranked(ranked_sparse_dense, pos)
            method_scores["BGE-M3+SparseOCR-DenseVLM"].append(m_sparse_dense)
            print(f"    BGE-M3+SparseOCR-DenseVLM  MRR={m_sparse_dense['MRR']:.3f}  R@1={m_sparse_dense['Recall@1']:.0f}  R@5={m_sparse_dense['Recall@5']:.0f}  ({ms:.0f}ms)")

        # Per-negative-type confusion
        method_map = {}
        if es: method_map["Elasticsearch BM25"] = ranked_bm25
        if bge: method_map["BGE-M3 raw"] = ranked_raw
        if bge:
            method_map["BGE-M3+VLM-structured"] = style_results["structured"][0]
        if bge: method_map["BGE-M3+LateFusion"] = ranked_fusion
        if bge: method_map["BGE-M3+SparseOCR-DenseVLM"] = ranked_sparse_dense

        for neg_type in set(neg_types):
            neg_idxs = [i for i, c in enumerate(candidates) if c["label"] == 0 and c["negative_type"] == neg_type]
            for method_label, ranked in method_map.items():
                rank_map = {idx: rank for rank, (idx, _) in enumerate(ranked, 1)}
                pos_rank = rank_map.get(pos, len(candidates) + 1)
                confused = sum(1 for ni in neg_idxs if rank_map.get(ni, 999) < pos_rank)
                type_scores[neg_type][method_label].append(confused / len(neg_idxs) if neg_idxs else 0.0)

        # Qualitative: collect if BM25 missed OR structured improved
        structured_ranked, m_struct = style_results.get("structured", ([], {}))
        bm25_r1 = m_bm25.get("Recall@1", -1) if es else -1
        struct_r1 = m_struct.get("Recall@1", -1) if m_struct else -1

        if es and bge and (bm25_r1 == 0 or (struct_r1 > bm25_r1)):
            qualitative_cases.append((
                q, candidates, pos,
                ranked_bm25, ranked_raw, structured_ranked, ranked_fusion, ranked_sparse_dense
            ))

        print()

    # ── Qualitative section ────────────────────────────────────────────────
    if qualitative_cases:
        print(f"\n{'#'*70}")
        print(f"  QUALITATIVE ANALYSIS — {len(qualitative_cases)} interesting case(s)")
        print(f"{'#'*70}")
        for case in qualitative_cases:
            print_qualitative_case(*case)
    else:
        print("\n  ℹ️  No interesting cases — all methods agree.")

    # ── Summary ────────────────────────────────────────────────────────────
    _print_summary(method_scores, type_scores)
    _save_results(method_scores, type_scores)


# ── OUTPUT HELPERS ───────────────────────────────────────────────────────────

def _avg(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _avg_m(scores: List[Dict[str, float]], metric: str) -> float:
    return _avg([s[metric] for s in scores])


def _print_summary(method_scores, type_scores):
    methods = list(method_scores.keys())
    metrics = ["MRR", "Recall@1", "Recall@5", "Recall@10", "NDCG@5", "NDCG@10"]
    W, C = 26, 10

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


def _save_results(method_scores, type_scores):
    out = {
        "overall": {
            method: {m: round(_avg_m(scores, m), 4) for m in ["MRR", "Recall@1", "Recall@5", "Recall@10", "NDCG@5", "NDCG@10"]}
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


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    path = os.path.abspath(DATASET_PATH)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    print(f"\nLoaded: {path}")
    print(f"Version: {dataset['version']}   Queries: {dataset['total_queries']}\n")
    run_benchmark(dataset)


if __name__ == "__main__":
    main()