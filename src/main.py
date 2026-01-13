import json
import logging
import sys
import time

import pika
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, StreamLostError

from src.config import config
from src.ingestion import process_task

logger = logging.getLogger("WorkerLogger")

def _callback(ch: BlockingChannel,
              method: spec.Basic.Deliver,
              _: spec.BasicProperties,
              body: bytes):
    try:
        logger.info(f"Received message: {method.delivery_tag}")
        data = json.loads(body)
        file_key = data.get("file_key")

        if not file_key:
            logger.warning("Received message with no file key. Discarding.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        logger.info(f"Processing file: {file_key}")
        process_task(file_key)

        logger.info(f"Task complete for {file_key}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Error processing {body}: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _start_worker():
    logger.info("Starting worker")

    while True:
        try:
            credentials = pika.PlainCredentials(username=config.RABBITMQ_USER, password=config.RABBITMQ_PASS)

            params = pika.ConnectionParameters(
                host=config.RABBITMQ_HOST,
                port=5672,
                credentials=credentials,
                heartbeat=300,  # Prevent disconnects for large pdfs
                blocked_connection_timeout=300
            )

            connection = pika.BlockingConnection(params)
            channel = connection.channel()

            queue_args = {
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": f"{config.QUEUE_NAME}_dl"
            }
            channel.queue_declare(queue=config.QUEUE_NAME, durable=True, arguments=queue_args)

            channel.queue_declare(queue=f"{config.QUEUE_NAME}_dl", durable=True)
            # One at a time
            channel.basic_qos(prefetch_count=1)

            logger.info(f"Watching queue: {config.QUEUE_NAME}")

            channel.basic_consume(
                queue=config.QUEUE_NAME,
                on_message_callback=_callback
            )

            channel.start_consuming()

        except (AMQPConnectionError, StreamLostError) as e:
            logger.warning(f"Connection lost: {e}. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.critical(f"Fatal Worker Error: {e}")
            time.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    _start_worker()