import hashlib
import logging
import uuid

import boto3
from botocore.exceptions import ClientError
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from src.config import config

logger = logging.getLogger('IngestionLogger')

s3 = boto3.client('s3',
                  endpoint_url=config.S3_ENDPOINT,
                  aws_access_key_id=config.S3_ACCESS_KEY,
                  aws_secret_access_key=config.S3_SECRET_KEY)

qdrant = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)

model = SentenceTransformer('all-MiniLM-L6-v2')

def _ensure_bucket_exist():
    try:
        s3.head_bucket(Bucket=config.S3_BUCKET)
        logger.info(f"Bucket '{config.S3_BUCKET}' exists.")
    except ClientError:
        print(f"Bucket '{config.S3_BUCKET}' not found. Creating it...")
        try:
            s3.create_bucket(Bucket=config.S3_BUCKET)
            logger.info(f"Created bucket '{config.S3_BUCKET}'")
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")

def _ensure_collection_exist():
    if not qdrant.collection_exists(config.QDRANT_COLLECTION_NAME):
        logger.info(f"Collection '{config.QDRANT_COLLECTION_NAME}' not found. Creating...")
        qdrant.create_collection(
            collection_name=config.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384, # Value for all-MiniLM-L6-v2
                distance=models.Distance.COSINE
            )
        )

def process_task(file_key: str):
    try:
        _ensure_bucket_exist()
        _ensure_collection_exist()
        logger.info(f"Processing {file_key}")

        temp_path = f'/tmp/{file_key}'
        s3.download_file(config.S3_BUCKET, file_key, temp_path)

        pdf_loader = PyPDFLoader(temp_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
        docs = pdf_loader.load_and_split(text_splitter)

        points = []
        for doc in docs:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            point_id = str(uuid.UUID(hex=content_hash))

            vector = model.encode(doc.page_content).tolist()

            points.append(models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "source": file_key,
                    "text": doc.page_content,
                    "page": doc.metadata.get("page", 0),
                }
            ))

        # Batch upsert
        qdrant.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points)

        logger.info(f"Processed {file_key} successfully")
    except Exception as e:
        logger.error(f"Unable to process {file_key} with error {e}")

