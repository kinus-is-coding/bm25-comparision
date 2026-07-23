from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

mapping = {
    "settings": {
        "index.max_ngram_diff": 2,
        "analysis": {
            "analyzer": {
                "ocr_ngram_analyzer": {
                    "tokenizer": "ocr_ngram_tokenizer",
                    "filter": ["lowercase", "asciifolding"]
                },
                "ocr_standard_analyzer": {
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"]
                }
            },
            "tokenizer": {
                "ocr_ngram_tokenizer": {
                    "type": "ngram",
                    "min_gram": 3,
                    "max_gram": 5,
                    "token_chars": ["letter", "digit"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "frame_id": {"type": "keyword"},
            "ocr": {
                "type": "text",
                "analyzer": "ocr_standard_analyzer",
                "fields": {
                    "ngram": {"type": "text", "analyzer": "ocr_ngram_analyzer"},
                    "raw": {"type": "keyword"}
                }
            }
        }
    }
}

if es.indices.exists(index="ocr"):
    es.indices.delete(index="ocr")

es.indices.create(index="ocr", body=mapping)
print("Elasticsearch 'ocr' index created successfully.")
