import json
import logging
import time

import pika
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, DuplicateConsumerTag

from src.config import config
from src.ingestion import process_task

logger = logging.getLogger("WorkerLogger")

def _callback(ch: BlockingChannel,
              method: spec.Basic.Deliver,
              _: spec.BasicProperties,
              body: bytes):
    try:
        logger.info(f"Received message")
        data = json.loads(body)
        file_key = data["file_key"]

        if not file_key:
            logger.info(f"Received message with no file key. Ignoring...")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        process_task(file_key)

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Worker error while processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def _start_worker():
    logger.info("Starting worker. Connecting to RabbitMQ")

    while True:
        try:
            credentials = pika.PlainCredentials(username=config.RABBITMQ_USER, password=config.RABBITMQ_PASS)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=5672, credentials=credentials)
            )
            channel = connection.channel()

            channel.queue_declare(queue=config.QUEUE_NAME, durable=True)
            # One at a time
            channel.basic_qos(prefetch_count=1)
            logger.info(f"Waiting messages for queue {config.QUEUE_NAME}")

            consumer_tag = channel.basic_consume(queue=config.QUEUE_NAME, on_message_callback=_callback)
            logger.info(f"Consumer tag: {consumer_tag}")

            channel.start_consuming()
        except AMQPConnectionError:
            seconds_to_retry = 5
            logger.info(f"Connection to RabbitMQ failed. Retrying in {seconds_to_retry} seconds")
            time.sleep(seconds_to_retry)
        except DuplicateConsumerTag as e:
            logger.error(f"Duplicate consumer tag error: {e}")


if __name__ == '__main__':
    _start_worker()