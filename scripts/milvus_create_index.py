from pymilvus import MilvusClient, DataType, Function, FunctionType

client = MilvusClient(uri="http://localhost:19530")
collection_name = "ocr_bm25"

if client.has_collection(collection_name):
    client.drop_collection(collection_name)

schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
schema.add_field(field_name="frame_id", datatype=DataType.INT64, is_primary=True)
schema.add_field(field_name="ocr", datatype=DataType.VARCHAR, max_length=512, enable_analyzer=True)
schema.add_field(field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR)

bm25_function = Function(
    name="ocr_bm25_fn",
    function_type=FunctionType.BM25,
    input_field_names=["ocr"],
    output_field_names=["sparse_vector"],
)
schema.add_function(bm25_function)

index_params = client.prepare_index_params()
index_params.add_index(
    field_name="sparse_vector",
    index_type="SPARSE_INVERTED_INDEX",
    metric_type="BM25"
)

client.create_collection(
    collection_name=collection_name,
    schema=schema,
    index_params=index_params,
)

print(f"Milvus '{collection_name}' collection created successfully.")
