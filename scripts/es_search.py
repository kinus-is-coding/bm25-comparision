from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")


def search_es(query: str, fuzziness: str = "AUTO"):
    print(f"\n--- Elasticsearch SOTA Searching for: '{query}' ---")
    res = es.search(
        index="ocr",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["ocr^3", "ocr.ngram^2", "ocr.raw^5"],
                    "type": "best_fields",
                    "fuzziness": fuzziness
                }
            }
        }
    )

    hits = res["hits"]["hits"]
    if not hits:
        print("  No hits found.")
        return

    for hit in hits:
        score = hit["_score"]
        source = hit["_source"]
        print(f"  [Score: {score:.4f}] Frame ID: {source['frame_id']} | Text: {source['ocr']}")


if __name__ == "__main__":
    search_es("Vietnam Airlines")
    search_es("Sam sumg")
