<div align="center">
  <h1> AI-Powered Observability Engine</h1>
  <p><b>"Google for System Metrics, but smarter."</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10-blue.svg?style=for-the-badge&logo=python)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
  [![Kubernetes](https://img.shields.io/badge/Kubernetes-Auto%20Scaling-326CE5.svg?style=for-the-badge&logo=kubernetes)](https://kubernetes.io/)
  [![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C.svg?style=for-the-badge&logo=prometheus)](https://prometheus.io/)
  [![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF.svg?style=for-the-badge&logo=github-actions)](https://github.com/features/actions)
  [![AWS](https://img.shields.io/badge/AWS-SQS%20%7C%20EKS%20%7C%20ECR-232F3E.svg?style=for-the-badge&logo=amazon-aws)](https://aws.amazon.com/)
</div>

---

##  The Problem it Solves (Real Use Case)
Normally, DevOps engineers and SREs have to write complex, error-prone PromQL queries to fetch live system data during high-stress incidents. 

**This system lets them just ask in English.** 

By wrapping a high-performance NLP-to-PromQL transpilation engine (powered by LLaMA3) around a real-time event processing backend, engineers can query their infrastructure as simply as using a search engine.

---

##  End-to-End Architecture

This is not a simple REST API. It is a full-stack, event-driven microservice ecosystem designed to production standards.

```mermaid
graph TD;
    subgraph 1. Event Generation & Processing
      Producer[Event Producer] -->|Pushes Orders| SQS[AWS SQS Queue];
      SQS -->|Polls & Processes| Processor[Event Processor];
      Processor -->|Exposes Metrics| Prom1[(Prometheus)];
    end
    
    subgraph 2. Natural Language Query Engine
      User-->|'Rate of high value orders?'|API[FastAPI Gateway];
      API-->|Check|Cache{In-Memory Cache};
      Cache-->|Miss|LLM[Groq LLM Engine];
      LLM-->|Transpiles to PromQL|Prom2[(Prometheus)];
      Cache-->|Hit|Prom2;
      Prom2-->|Live Data|API;
      API-->|Result|User;
    end
```

---

##  Key Engineering Features (Production Grade)

- **AI Translation Layer:** Uses Groq to dynamically transpile natural language into precise PromQL queries.
- **Bulletproof Resiliency:** 
  - **LLM Fallback:** If the LLM API rate-limits or fails, a local regex-based engine instantly takes over with zero downtime.
  - **Database Graceful Degradation:** If Prometheus is unreachable, the API intercepts the `ConnectionError` and returns a safe "System Offline" JSON response instead of a 500 server crash.
- **⚡ In-Memory Compiler Cache:** Redundant natural language queries bypass the LLM entirely, pulling the translated PromQL from RAM to drastically reduce latency and API costs.
- **☸️ Kubernetes Auto-Scaling (HPA):** If CPU utilization exceeds 60% during a traffic spike, the Horizontal Pod Autoscaler dynamically scales the API from 1 pod up to 5 pods to maintain low latency.
- **📈 Self-Monitoring API:** The system monitors itself. It exposes a `/metrics` endpoint tracking `ask_requests_total`, `cache_hits`, error rates, and query latency histograms.
- **🔄 Dual CI/CD Pipelines:** Fully automated build, test, and deployment pipelines written for both **Jenkins** and **GitHub Actions**.

---

##  The Tech Stack

| Technology | Role |
|------------|------|
| **Python / FastAPI** | High-performance, async backend framework. |
| **AWS SQS** | Decoupled message broker for the event-driven backend. |
| **Prometheus & Grafana** | Time-series database and visualization dashboards. |
| **Kubernetes (EKS)** | Orchestrates containers, manages state, and scales pods. |
| **Docker & ECR** | Containerization and secure image registry. |
| **Terraform** | Infrastructure as Code (IaC) to provision the AWS cloud. |
| **Jenkins / GH Actions** | Continuous Integration and Deployment (CI/CD). |

---

##  How to Run Locally (Docker Compose)

You can run the entire distributed system on your local machine with a single command. 

1. **Configure Environment:**
   Create a `.env` file in the root directory with your AWS credentials:
   ```env
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=ap-south-1
   SQS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/...
   ```

2. **Boot the Infrastructure:**
   ```bash
   docker compose up -d --build
   ```
   *This starts the Producer, Processor, API, Prometheus, and Grafana simultaneously.*

3. **Ask a Question:**
   ```bash
   curl -X POST http://localhost:8080/ask \
        -H "Content-Type: application/json" \
        -d '{"question": "rate of high value orders over 5 minutes"}'
   ```

4. **Trigger the Load Test (Autoscaling Demo):**
   ```bash
   python load_test.py --requests 1000 --concurrency 50
   ```

---

##  Cloud Deployment (Kubernetes + Terraform)

To deploy to a live cloud environment:

1. **Provision Infrastructure:**
   ```bash
   cd terraform
   terraform init && terraform apply -auto-approve
   ```
2. **Deploy Microservices:**
   ```bash
   kubectl apply -k k8s/base/
   kubectl apply -f k8s/api/api_hpa.yaml
   ```

---

