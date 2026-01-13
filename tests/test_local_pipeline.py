import urllib.request

import pika
import json
import boto3
import os

S3_ENDPOINT = 'http://localhost:8333'
S3_BUCKET = 'documents'
AWS_ACCESS_KEY = 'accessKey'
AWS_SECRET_KEY = 'secretKey'

RABBIT_HOST = 'localhost'
QUEUE_NAME = 'ingest_queue'


def upload_file(file_path):
    print(f"Uploading {file_path} to SeaweedFS...")

    s3 = boto3.client('s3',
                      endpoint_url=S3_ENDPOINT,
                      aws_access_key_id=AWS_ACCESS_KEY,
                      aws_secret_access_key=AWS_SECRET_KEY                      )

    file_name = os.path.basename(file_path)

    try:
        s3.create_bucket(Bucket=S3_BUCKET)
    except:
        pass

    s3.upload_file(file_path, S3_BUCKET, file_name)
    print("Upload Complete.")
    return file_name


def trigger_worker(file_name):
    print(f"Sending job for '{file_name}' to RabbitMQ...")

    credentials = pika.PlainCredentials('user', 'pass')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBIT_HOST, port=5672, credentials=credentials)
    )
    channel = connection.channel()

    queue_args = {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": f"{QUEUE_NAME}_dl"
    }

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments=queue_args
    )

    message = json.dumps({"file_key": file_name})

    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,
        ))

    print(f"Job sent worker will pick it up.")
    connection.close()


if __name__ == "__main__":
    pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    local_filename = "valid_test.pdf"

    print(f"Downloading valid PDF from {pdf_url}...")
    urllib.request.urlretrieve(pdf_url, local_filename)

    uploaded_name = upload_file(local_filename)
    trigger_worker(uploaded_name)