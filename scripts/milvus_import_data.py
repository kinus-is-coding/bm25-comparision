import pandas as pd
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")
collection_name = "ocr_bm25"

df = pd.read_csv("data/ocr.csv")
data = [
    {
        "frame_id": int(row["frame_id"]),
        "ocr": str(row["ocr"])
    }
    for _, row in df.iterrows()
]

res = client.insert(collection_name=collection_name, data=data)
print(f"Milvus: Imported {res['insert_count']} records into '{collection_name}' collection.")
