import time
from elasticsearch import Elasticsearch
from pymilvus import MilvusClient

# Initialize clients
es = Elasticsearch("http://localhost:9200")
milvus_client = MilvusClient(uri="http://localhost:19530")
milvus_collection = "ocr_bm25"


def benchmark_query(category_name: str, query: str, es_fuzziness: str = "AUTO"):
    print("=" * 80)
    print(f"📌 TEST CASE: {category_name}")
    print(f"🔍 QUERY: '{query}'")
    print("=" * 80)

    # 1. Elasticsearch SOTA Search
    start_es = time.perf_counter()
    es_res = es.search(
        index="ocr",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["ocr^3", "ocr.ngram^2", "ocr.raw^5"],
                    "type": "best_fields",
                    "fuzziness": es_fuzziness
                }
            }
        }
    )
    latency_es_ms = (time.perf_counter() - start_es) * 1000
    es_hits = es_res["hits"]["hits"]

    # 2. Milvus Native BM25 Search
    start_milvus = time.perf_counter()
    milvus_res = milvus_client.search(
        collection_name=milvus_collection,
        data=[query],
        anns_field="sparse_vector",
        limit=5,
        output_fields=["frame_id", "ocr"],
        search_params={"metric_type": "BM25", "params": {}}
    )
    latency_milvus_ms = (time.perf_counter() - start_milvus) * 1000
    milvus_hits = milvus_res[0] if milvus_res else []

    # Display Side-by-Side Comparison
    print(f"\n--- 🟢 Elasticsearch SOTA (Latency: {latency_es_ms:.2f} ms) ---")
    if not es_hits:
        print("  ❌ No hits found.")
    for hit in es_hits:
        print(f"  [Score: {hit['_score']:.4f}] Frame {hit['_source']['frame_id']}: {hit['_source']['ocr']}")

    print(f"\n--- 🔴 Milvus Native BM25 (Latency: {latency_milvus_ms:.2f} ms) ---")
    if not milvus_hits:
        print("  ❌ No hits found.")
    for hit in milvus_hits:
        entity = hit["entity"]
        print(f"  [Score: {hit['distance']:.4f}] Frame {entity['frame_id']}: {entity['ocr']}")
    print("\n")


if __name__ == "__main__":
    test_cases = [
        ("1. LỖI OCR DÍNH TỪ (No space / Joined Words)", "Hãng máy bay", "AUTO"),
        ("2. TIẾNG VIỆT CÓ DẤU VS KHÔNG DẤU (ASCII Folding)", "city", "AUTO"),
        ("3. DẤU GẠCH NGANG / KÝ TỰ ĐẶC BIỆT (Hyphenation)", "iPhone 16", "AUTO"),
        ("4. TỪ TÁCH NỔI LỖI CHÍNH TẢ (Split-word Typos)", "Sam sumg", "AUTO"),
        ("5. VIẾT TẮT / LỖI MẤT KÝ TỰ (Partial String OCR)", "Canon EOS", "AUTO"),
    ]

    for category, q, fuzz in test_cases:
        benchmark_query(category, q, es_fuzziness=fuzz)
