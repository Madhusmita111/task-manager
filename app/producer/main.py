import json
import random
import time
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

QUEUE_URL = os.getenv("SQS_QUEUE_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")  # Support local emulators if specified

def get_sqs_client():
    """
    Retrieves a boto3 SQS client with integrated initialization retry logic
    to tolerate transient cloud network issues or queue start delay.
    """
    retries = 5
    backoff = 2
    for i in range(retries):
        try:
            client_args = {"region_name": AWS_REGION}
            if AWS_ENDPOINT_URL:
                client_args["endpoint_url"] = AWS_ENDPOINT_URL
            
            sqs_client = boto3.client('sqs', **client_args)
            # Perform a test queue attribute fetch or simple validation to confirm connection
            if QUEUE_URL:
                sqs_client.get_queue_attributes(QueueUrl=QUEUE_URL, AttributeNames=['QueueArn'])
            
            print(f"[PRODUCER INFO] Successfully connected to SQS at: {QUEUE_URL or 'AWS Default'}", flush=True)
            return sqs_client
        except Exception as e:
            print(f"[PRODUCER WARNING] Initialization attempt {i+1}/{retries} failed: {str(e)}. Retrying in {backoff}s...", flush=True)
            time.sleep(backoff)
            backoff *= 2
            
    # Return client anyway and let runtime calls attempt self-healing
    client_args = {"region_name": AWS_REGION}
    if AWS_ENDPOINT_URL:
        client_args["endpoint_url"] = AWS_ENDPOINT_URL
    return boto3.client('sqs', **client_args)


def generate_order():
    """
    Generates a structured order event representing business transactions.
    """
    return {
        "order_id": random.randint(1000, 9999),
        "user_id": random.randint(1, 100),
        "amount": random.randint(100, 10000),
        "timestamp": time.time()
    }


def send_to_sqs(sqs_client, order):
    """
    Sends an event to the AWS SQS Queue, handling transport-level failures gracefully.
    """
    if not QUEUE_URL:
        print("[PRODUCER ERROR] SQS_QUEUE_URL environment variable is not defined!", flush=True)
        return False

    try:
        sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(order)
        )
        print(f"[PRODUCER SUCCESS] Sent Order: {order}", flush=True)
        return True
    except Exception as e:
        print(f"[PRODUCER ERROR] Failed to send message to SQS: {str(e)}", flush=True)
        return False


def main():
    print("[PRODUCER START] Starting order event generator daemon...", flush=True)
    
    sqs_client = get_sqs_client()
    
    while True:
        try:
            order = generate_order()
            success = send_to_sqs(sqs_client, order)
            
            # If sending failed, retry SQS connection in case the connection was broken
            if not success:
                print("[PRODUCER RECOVERY] Re-initializing SQS client...", flush=True)
                sqs_client = get_sqs_client()
                time.sleep(5)  # Wait longer on error before next cycle
                continue

            time.sleep(random.uniform(1.0, 3.0))  # Dynamic production pacing
        except KeyboardInterrupt:
            print("[PRODUCER SHUTDOWN] Terminating producer gracefully...", flush=True)
            break
        except Exception as e:
            print(f"[PRODUCER CRITICAL] Unexpected main loop error: {str(e)}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()