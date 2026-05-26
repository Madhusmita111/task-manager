import json
import time
import boto3
import os
from prometheus_client import start_http_server, Counter

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

sqs = boto3.client('sqs', region_name=AWS_REGION)

orders_processed = Counter('orders_processed_total', 'Total processed orders')
high_value_orders = Counter('high_value_orders_total', 'High value orders')


def process_order(order):
    orders_processed.inc()

    if order["amount"] > 5000:
        order["type"] = "HIGH"
        high_value_orders.inc()
    else:
        order["type"] = "NORMAL"

    return order


def receive_messages():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )
    return response.get("Messages", [])


def delete_message(receipt_handle):
    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle
    )


def main():
    start_http_server(8000)

    while True:
        try:
            messages = receive_messages()

            if not messages:
                continue

            for msg in messages:
                order = json.loads(msg["Body"])
                processed = process_order(order)

                print("Processed:", processed, flush=True)

                delete_message(msg["ReceiptHandle"])

        except Exception as e:
            print("Error:", str(e), flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
