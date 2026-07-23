from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")
print("Connected to Elasticsearch successfully!")
print("Server Version:", es.info()["version"]["number"])
