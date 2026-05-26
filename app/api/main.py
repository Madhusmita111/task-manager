from fastapi import FastAPI
from pydantic import BaseModel
from llm import get_query_from_llm
from prometheus_client import query_prometheus

app = FastAPI()

class Question(BaseModel):
    question: str

def extract_value(prom_result):
    try:
        return prom_result["data"]["result"][0]["value"][1]
    except:
        return None

@app.post("/ask")
def ask(q: Question):
    try:
        # Step 1: LLM generates query
        prom_query = get_query_from_llm(q.question)

        # Step 2: Query Prometheus
        result = query_prometheus(prom_query)

        # Step 3: Extract value
        value = extract_value(result)

        # Step 4: Clean response
        if value:
            return {
                "question": q.question,
                "query": prom_query,
                "answer": f"The result is {value}"
            }
        else:
            return {
                "question": q.question,
                "query": prom_query,
                "answer": "No data available"
            }

    except Exception as e:
        return {"error": str(e)}