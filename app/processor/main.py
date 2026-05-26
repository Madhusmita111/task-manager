import json
import time
import boto3
import os
from prometheus_client import start_http_server, Counter

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")  # Support local SQS emulator if specified

# Prometheus Metrics Definitions
orders_processed = Counter('orders_processed_total', 'Total processed orders')
high_value_orders = Counter('high_value_orders_total', 'Total processed high-value orders (> 5000)')
processing_errors = Counter('processing_errors_total', 'Total errors encountered during SQS consumption/processing')

def get_sqs_client():
    """
    Acquires an active boto3 SQS client, attempting connection multiple times 
    with exponential backoff to handle transient startup delay or AWS offline.
    """
    retries = 5
    backoff = 2
    for i in range(retries):
        try:
            client_args = {"region_name": AWS_REGION}
            if AWS_ENDPOINT_URL:
                client_args["endpoint_url"] = AWS_ENDPOINT_URL
            
            sqs_client = boto3.client('sqs', **client_args)
            if QUEUE_URL:
                sqs_client.get_queue_attributes(QueueUrl=QUEUE_URL, AttributeNames=['QueueArn'])
            
            print(f"[PROCESSOR INFO] Successfully connected to SQS at: {QUEUE_URL or 'AWS Default'}", flush=True)
            return sqs_client
        except Exception as e:
            print(f"[PROCESSOR WARNING] SQS connection attempt {i+1}/{retries} failed: {str(e)}. Retrying in {backoff}s...", flush=True)
            time.sleep(backoff)
            backoff *= 2

    # Fallback to standard instantiation if retry exhausted
    client_args = {"region_name": AWS_REGION}
    if AWS_ENDPOINT_URL:
        client_args["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client('sqs', **client_args)


def process_order(order):
    """
    Executes core business logic on the order payload and updates metrics.
    """
    orders_processed.inc()

    # Amount-based classification
    amount = order.get("amount", 0)
    if amount > 5000:
        order["type"] = "HIGH"
        high_value_orders.inc()
    else:
        order["type"] = "NORMAL"

    return order


def receive_messages(sqs_client):
    """
    Fetches message batches from SQS.
    """
    if not QUEUE_URL:
        raise ValueError("SQS_QUEUE_URL environment variable is not defined.")

    response = sqs_client.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5  # Long polling
    )
    return response.get("Messages", [])


def delete_message(sqs_client, receipt_handle):
    """
    Removes a successfully processed message from SQS to avoid reprocessing.
    """
    sqs_client.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle
    )


def main():
    print("[PROCESSOR START] Starting SQS metric processor daemon...", flush=True)
    
    # Start Prometheus server on port 8000
    try:
        start_http_server(8000)
        print("[PROCESSOR INFO] Prometheus scraping metrics server active on port 8000", flush=True)
    except Exception as e:
        print(f"[PROCESSOR ERROR] Could not start Prometheus metrics exporter: {str(e)}", flush=True)

    sqs_client = get_sqs_client()

    while True:
        try:
            messages = receive_messages(sqs_client)

            if not messages:
                continue

            for msg in messages:
                try:
                    order = json.loads(msg["Body"])
                    processed = process_order(order)
                    print(f"[PROCESSOR SUCCESS] Processed Order: {processed}", flush=True)

                    # Delete message from SQS queue on successful process
                    delete_message(sqs_client, msg["ReceiptHandle"])
                except json.JSONDecodeError as jde:
                    processing_errors.inc()
                    print(f"[PROCESSOR ERROR] Failed to parse message body as JSON: {str(jde)}. Deleting bad payload.", flush=True)
                    delete_message(sqs_client, msg["ReceiptHandle"])
                except Exception as ex:
                    processing_errors.inc()
                    print(f"[PROCESSOR ERROR] Error executing message processing: {str(ex)}", flush=True)

        except Exception as e:
            processing_errors.inc()
            print(f"[PROCESSOR CRITICAL] Error polling queue or connecting to SQS: {str(e)}", flush=True)
            print("[PROCESSOR RECOVERY] Attempting to reconnect SQS client...", flush=True)
            sqs_client = get_sqs_client()
            time.sleep(5)  # Wait on connection error before retry


if __name__ == "__main__":
    main()
