import pandas as pd
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch("http://localhost:9200")

df = pd.read_csv("data/ocr.csv")

actions = [
    {
        "_index": "ocr",
        "_id": str(row["frame_id"]),
        "_source": {
            "frame_id": int(row["frame_id"]),
            "ocr": str(row["ocr"])
        }
    }
    for _, row in df.iterrows()
]

success, _ = helpers.bulk(es, actions)
print(f"Elasticsearch: Imported {success} records into 'ocr' index.")
