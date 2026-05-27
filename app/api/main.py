from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from llm import get_query_from_llm
import requests
import os
import json
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

# ------------------------------------------------------------------------------
# Structured JSON Logging Setup
# ------------------------------------------------------------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(record.created)),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if hasattr(record, "extra_info"):
            log_data.update(record.extra_info)
        return json.dumps(log_data)

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

# Console Handler
ch = logging.StreamHandler()
ch.setFormatter(JSONFormatter())
logger.addHandler(ch)

# ------------------------------------------------------------------------------
# App & Metrics Configuration
# ------------------------------------------------------------------------------
app = FastAPI(
    title="AI-Powered Observability API",
    description="DevOps NLP PromQL Query Engine with Dynamic Caching & Observability",
    version="1.0.0"
)

# In-memory translation cache: maps "english query" -> "PromQL string"
# This acts as a high-performance compiler cache, avoiding redundant LLM queries
translation_cache = {}

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

# Custom Prometheus Instrumentation
ask_requests = Counter("ask_requests_total", "Total /ask requests received")
ask_errors = Counter("ask_errors_total", "Total failed /ask requests")
cache_hits = Counter("cache_hits_total", "Total PromQL cache hits")
cache_misses = Counter("cache_misses_total", "Total PromQL cache misses")
ask_latency = Histogram(
    "ask_latency_seconds", 
    "Latency of /ask endpoint execution in seconds",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ------------------------------------------------------------------------------
# Request & Response schemas
# ------------------------------------------------------------------------------
class QuestionRequest(BaseModel):
    question: str

# ------------------------------------------------------------------------------
# Intent Validation & Business Logic Guards
# ------------------------------------------------------------------------------
def is_valid_question(question: str) -> bool:
    """
    Ensures the user intent focuses on available business metrics
    to prevent unrelated processing or system noise.
    """
    keywords = ["order", "orders", "value", "sales", "processed", "rate", "sum", "total"]
    return any(k in question.lower() for k in keywords)

# ------------------------------------------------------------------------------
# Prometheus Query Executor
# ------------------------------------------------------------------------------
def query_prometheus(query: str) -> dict:
    """
    Executes a PromQL query directly against the Prometheus HTTP API.
    Raises ConnectionError if Prometheus is unreachable.
    """
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        if response.status_code != 200:
            return {"error": f"Prometheus returned status {response.status_code}", "raw": response.text}
        return response.json()
    except Exception as e:
        logger.error(
            f"Failed to query Prometheus at {PROMETHEUS_URL}", 
            extra={"extra_info": {"error": str(e), "query": query}}
        )
        raise ConnectionError(f"Prometheus connection failure: {str(e)}")

# ------------------------------------------------------------------------------
# Metric Value Extraction Helper
# ------------------------------------------------------------------------------
def extract_value(prom_result: dict) -> str:
    """
    Parses Prometheus API responses safely, returning values or structured placeholders.
    """
    try:
        data = prom_result.get("data", {})
        result = data.get("result", [])
        if not result:
            return "0 (No data active)"
        
        # Standard instantaneous or vector metric return [timestamp, value]
        value = result[0]["value"][1]
        
        # Round numerical values to two decimal places if float
        try:
            return f"{float(value):.2f}"
        except ValueError:
            return str(value)
    except Exception:
        return "No data available"

# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------
@app.post("/ask")
def ask(data: QuestionRequest):
    question = data.question
    ask_requests.inc()
    start_time = time.time()

    # 1. Input sanity check
    if not question or len(question.strip()) < 3:
        ask_errors.inc()
        logger.warning("Empty or invalid request received at /ask")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid question: Please ask a meaningful metric query."
        )

    clean_question = question.strip().lower()

    # 2. Business intent validation
    if not is_valid_question(clean_question):
        ask_errors.inc()
        logger.warning(f"Business intent validation failed for question: '{question}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic not supported. Please query order processing metrics or sales performance."
        )

    try:
        # 3. Cache Check (PromQL translation cache)
        cached = False
        if clean_question in translation_cache:
            cache_hits.inc()
            cached = True
            promql_query = translation_cache[clean_question]
            logger.info(
                "PromQL query translation fetched from cache", 
                extra={"extra_info": {"question": question, "promql": promql_query, "cache_hit": True}}
            )
        else:
            cache_misses.inc()
            # 4. Transpile Natural Language to PromQL via LLM/Fallback
            promql_query = get_query_from_llm(question)
            translation_cache[clean_question] = promql_query
            logger.info(
                "PromQL query translated via LLM engine", 
                extra={"extra_info": {"question": question, "promql": promql_query, "cache_hit": False}}
            )

        # 5. Fetch live time-series data from Prometheus
        prom_response = query_prometheus(promql_query)

        # 6. Safe response formatting
        if "error" in prom_response:
            raise ValueError(prom_response["error"])

        value = extract_value(prom_response)

        execution_time = time.time() - start_time
        ask_latency.observe(execution_time)

        logger.info(
            "Successfully processed metric request",
            extra={
                "extra_info": {
                    "question": question,
                    "promql": promql_query,
                    "result_value": value,
                    "latency_ms": round(execution_time * 1000, 2),
                    "cached": cached
                }
            }
        )

        return {
            "status": "success",
            "question": question,
            "promql": promql_query,
            "answer": f"The current value is {value}",
            "cached_translation": cached,
            "raw_prometheus_data": prom_response.get("data", {}).get("result", [])
        }

    except ConnectionError as e:
        ask_errors.inc()
        # High resiliency fallback: return a safe response indicating server disruption
        # but displaying the translated query they would have executed.
        logger.error(f"Fallback initiated due to Prometheus connection failure: {str(e)}")
        return {
            "status": "partial_success",
            "question": question,
            "promql": promql_query if 'promql_query' in locals() else "Unknown",
            "answer": "Service partially offline. Prometheus DB is currently unreachable.",
            "error_log": str(e),
            "fallback_active": True
        }

    except Exception as e:
        ask_errors.inc()
        logger.error(
            f"Unexpected failure during /ask execution: {str(e)}",
            extra={"extra_info": {"question": question}}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while compiling your metrics query: {str(e)}"
        )

@app.get("/metrics")
def metrics():
    """
    Exposes raw Prometheus metrics to be scraped by the Prometheus daemon.
    """
    return Response(generate_latest(), media_type="text/plain")

@app.get("/health")
def health():
    """
    Self-health probe used by orchestrators to confirm API availability.
    """
    return {"status": "healthy", "timestamp": time.time()}