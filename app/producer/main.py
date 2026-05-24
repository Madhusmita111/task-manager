import json
import random
import time
import boto3
import os
from dotenv import load_dotenv
load_dotenv()

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

sqs = boto3.client('sqs', region_name=AWS_REGION)

def generate_order():
    return {
        "order_id": random.randint(1000, 9999),
        "user_id": random.randint(1, 100),
        "amount": random.randint(100, 10000)
    }

def send_to_sqs(order):
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(order)
    )

def main():
    while True:
        order = generate_order()
        send_to_sqs(order)
        print("Sent Order:", order)
        time.sleep(2)

if __name__ == "__main__":
    main()