from fastapi import FastAPI
from pydantic import BaseModel
from llm import get_query_from_llm
from prometheus_client import Counter
import requests
import os

# -----------------------
# App setup
# -----------------------
app = FastAPI()
cache = {}

# -----------------------
# Prometheus config
# -----------------------
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL",
    "http://prometheus-service:9090"
)

# -----------------------
# Metrics
# -----------------------
ask_requests = Counter("ask_requests_total", "Total /ask requests")

# -----------------------
# Request model
# -----------------------
class Question(BaseModel):
    question: str

# -----------------------
# Prometheus Query Function
# -----------------------
def query_prometheus(query: str):
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Extract value helper
# -----------------------
def extract_value(prom_result):
    try:
        return prom_result["data"]["result"][0]["value"][1]
    except:
        return "No data"

# -----------------------
# Main Endpoint
# -----------------------
@app.post("/ask")
async def ask(data: Question):
    question = data.question

    ask_requests.inc()

    # 🔥 CACHE HIT
    if question in cache:
        return {
            "question": question,
            "query": cache[question]["query"],
            "answer": cache[question]["answer"],
            "cached": True
        }

    # 🔥 LLM → PromQL
    query = get_query_from_llm(question)

    # 🔥 Prometheus Query
    result = query_prometheus(query)

    value = extract_value(result)

    answer = f"The result is {value}"

    # 🔥 Cache store
    cache[question] = {
        "query": query,
        "answer": answer
    }

    return {
        "question": question,
        "query": query,
        "answer": answer,
        "cached": False
    }

# -----------------------
# Health Check
# -----------------------
@app.get("/health")
def health():
    return {"status": "ok"}