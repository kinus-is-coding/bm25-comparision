from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")
print("Connected to Milvus successfully!")
print("Existing Collections:", client.list_collections())
