# bm25-comparision
Bước 1: Test kết nối 2 bên
bash
python scripts/es_test_connection.py
python scripts/milvus_test_connection.py
Bước 2: Tạo Index & Import dữ liệu
Elasticsearch:
bash
python scripts/es_create_index.py
python scripts/es_import_data.py
Milvus:
bash
python scripts/milvus_create_index.py
python scripts/milvus_import_data.py
Bước 3: Test Search đơn lẻ hoặc So sánh Benchmark
bash
python scripts/es_search.py
python scripts/milvus_search.py
# Benchmark song song 5 kịch bản thực tế
python scripts/compare_search.py
