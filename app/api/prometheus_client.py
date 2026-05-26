import requests

PROM_URL = "http://prometheus-service:9090/api/v1/query"

def query_prometheus(query):
    response = requests.get(PROM_URL, params={"query": query})
    return response.json()