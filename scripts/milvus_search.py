from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")
collection_name = "ocr_bm25"


def search_milvus(query: str, top_k: int = 5):
    print(f"\n--- Milvus BM25 Searching for: '{query}' ---")
    res = client.search(
        collection_name=collection_name,
        data=[query],
        anns_field="sparse_vector",
        limit=top_k,
        output_fields=["frame_id", "ocr"],
        search_params={"metric_type": "BM25", "params": {}}
    )

    hits = res[0]
    if not hits:
        print("  No hits found.")
        return

    for hit in hits:
        score = hit["distance"]
        entity = hit["entity"]
        print(f"  [Score: {score:.4f}] Frame ID: {entity['frame_id']} | Text: {entity['ocr']}")


if __name__ == "__main__":
    search_milvus("Vietnam Airlines")
    search_milvus("Sam sumg")
