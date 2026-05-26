import pytest
from fastapi.testclient import TestClient
import os
import sys

# Append the directory containing main and llm to python path for testing
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, is_valid_question, translation_cache
from llm import local_keyword_translator, validate_query

client = TestClient(app)

# ------------------------------------------------------------------------------
# 1. Test Intent Validation & Business Logic Guards
# ------------------------------------------------------------------------------
def test_intent_validation():
    # Valid business-related questions
    assert is_valid_question("high value orders per minute") is True
    assert is_valid_question("total processed orders") is True
    assert is_valid_question("sales performance") is True
    assert is_valid_question("rate of orders") is True

    # Invalid/unrelated questions
    assert is_valid_question("what is the weather today") is False
    assert is_valid_question("show me a recipe for pasta") is False
    assert is_valid_question("deploy database") is False


# ------------------------------------------------------------------------------
# 2. Test Local Rule-Based Keyword Translation Fallback
# ------------------------------------------------------------------------------
def test_local_keyword_translator():
    # High value order patterns
    q1 = "how many high value orders processed per minute?"
    assert local_keyword_translator(q1) == "rate(high_value_orders_total[1m])"

    # Default order processing rate
    q2 = "rate of processed orders?"
    assert local_keyword_translator(q2) == "rate(orders_processed_total[1m])"

    # Sum aggregations
    q3 = "total processed orders count"
    assert local_keyword_translator(q3) == "sum(orders_processed_total)"

    # Over customs
    q4 = "rate of orders over 5 minutes"
    assert local_keyword_translator(q4) == "rate(orders_processed_total[5m])"


# ------------------------------------------------------------------------------
# 3. Test Security Sanitization & Injection Interception
# ------------------------------------------------------------------------------
def test_query_sanitization():
    # Valid safe queries
    assert validate_query("rate(orders_processed_total[1m])") == "rate(orders_processed_total[1m])"
    assert validate_query("sum(high_value_orders_total)") == "sum(high_value_orders_total)"

    # Unsafe characters
    with pytest.raises(ValueError, match="Query contains unsafe or illegal characters"):
        validate_query("rate(orders_processed_total[1m]); DROP TABLE orders;")

    # Missing whitelisted metrics
    with pytest.raises(ValueError, match="Query does not reference any valid system metrics"):
        validate_query("rate(system_cpu_usage[5m])")

    # Command execution attempt
    with pytest.raises(ValueError, match="Query contains forbidden keywords"):
        validate_query("orders_processed_total + __import__('os').system('rm -rf /')")


# ------------------------------------------------------------------------------
# 4. Test API Endpoints using FastAPI TestClient
# ------------------------------------------------------------------------------
def test_ask_endpoint_basic_validation():
    # Empty question
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 400
    assert "Invalid question" in response.json()["detail"]

    # Short question
    response = client.post("/ask", json={"question": "ok"})
    assert response.status_code == 400

    # Unrelated intent question
    response = client.post("/ask", json={"question": "who is the prime minister of India?"})
    assert response.status_code == 400
    assert "Topic not supported" in response.json()["detail"]


def test_ask_endpoint_successful_caching_and_translation(monkeypatch):
    # Mock query_prometheus to return successful response
    mock_metric_result = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {},
                    "value": [1680000000, "15.50"]
                }
            ]
        }
    }
    
    def mock_query(query):
        return mock_metric_result

    # Inject mock into main executor
    monkeypatch.setattr("main.query_prometheus", mock_query)
    
    # Ensure cache is empty initially
    translation_cache.clear()

    # First Query (Cache Miss)
    payload = {"question": "how many orders are processed per minute?"}
    response1 = client.post("/ask", json=payload)
    assert response1.status_code == 200
    res_data1 = response1.json()
    assert res_data1["status"] == "success"
    assert res_data1["cached_translation"] is False
    assert "15.50" in res_data1["answer"]
    assert res_data1["promql"] == "rate(orders_processed_total[1m])"

    # Second Query with same text (Cache Hit)
    response2 = client.post("/ask", json=payload)
    assert response2.status_code == 200
    res_data2 = response2.json()
    assert res_data2["status"] == "success"
    assert res_data2["cached_translation"] is True
    assert "15.50" in res_data2["answer"]


def test_ask_endpoint_prometheus_down_fallback(monkeypatch):
    # Mock query_prometheus to raise ConnectionError (simulation of server downtime)
    def mock_query_error(query):
        raise ConnectionError("Connection refused by Prometheus server")

    monkeypatch.setattr("main.query_prometheus", mock_query_error)
    
    payload = {"question": "high value orders rate per minute"}
    response = client.post("/ask", json=payload)
    
    # Assert API returns a resilient partial_success rather than 500 error
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "partial_success"
    assert res_data["fallback_active"] is True
    assert "Prometheus DB is currently unreachable" in res_data["answer"]
    assert res_data["promql"] == "rate(high_value_orders_total[1m])"
