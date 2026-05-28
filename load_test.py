import requests
import concurrent.futures
import time
import argparse

def send_request(url, index):
    payload = {"question": "rate of high value orders over 5 minutes"}
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=5)
        latency = time.time() - start
        return {"index": index, "status_code": response.status_code, "latency": latency}
    except Exception as e:
        return {"index": index, "status_code": "ERROR", "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Load test the AI Metrics API to trigger HPA.")
    parser.add_argument("--url", default="http://localhost:8080/ask", help="API Endpoint URL")
    parser.add_argument("--requests", type=int, default=500, help="Total number of requests to send")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent workers")
    args = parser.parse_args()

    print(f"Starting Load Test against {args.url}")
    print(f"Total Requests: {args.requests} | Concurrency: {args.concurrency}\n")

    start_time = time.time()
    success_count = 0
    error_count = 0

    # Using ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(send_request, args.url, i) for i in range(args.requests)]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result["status_code"] == 200:
                success_count += 1
            else:
                error_count += 1
            
            # Print progress every 50 requests
            if (success_count + error_count) % 50 == 0:
                print(f"Sent {success_count + error_count}/{args.requests} requests...")

    total_time = time.time() - start_time
    print("Load Test Completed!")
    print("--------------------------------------------------")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Requests/Second: {args.requests / total_time:.2f} rps")
    print(f"Successful Requests: {success_count}")
    print(f"Failed Requests: {error_count}")
    print("--------------------------------------------------")
    print("👉 Now, check your Kubernetes cluster to see if the HPA triggered:")
    print("Run command: kubectl get hpa")
    print("Run command: kubectl get pods -l app=api")

if __name__ == "__main__":
    main()
