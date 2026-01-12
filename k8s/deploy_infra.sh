#!/bin/bash
set -e

if [ -z "$RABBITMQ_PASS" ] || [ -z "$S3_ADMIN_KEY" ] || [ -z "$S3_ADMIN_SECRET" ]; then
  echo "Error: Missing required environment variables."
  exit 1
fi

kubectl create secret generic rabbitmq-secret \
  --from-literal=rabbitmq-password="$RABBITMQ_PASS" \
  --dry-run=client -o yaml | kubectl apply -f -

S3_JSON=$(printf '{"identities":[{"name":"admin","credentials":[{"accessKey":"%s","secretKey":"%s"}]}]}' "$S3_ADMIN_KEY" "$S3_ADMIN_SECRET")

kubectl create secret generic seaweedfs-s3-secret \
  --from-literal=s3_users.json="$S3_JSON" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic app-secrets \
  --from-literal=RABBITMQ_PASS="$RABBITMQ_PASS" \
  --from-literal=S3_ACCESS_KEY="$S3_ADMIN_KEY" \
  --from-literal=S3_SECRET_KEY="$S3_ADMIN_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

helm repo add bitnami https://charts.bitnami.com/bitnami > /dev/null
helm repo add qdrant https://qdrant.github.io/qdrant-helm > /dev/null
helm repo add seaweedfs https://seaweedfs.github.io/seaweedfs/helm > /dev/null
helm repo update > /dev/null

echo "Deploying rabbitmq"
kubectl apply -f k8s/rabbitmq-native.yaml

echo "Waiting for RabbitMQ"
kubectl wait --for=condition=ready pod -l app=rabbitmq --timeout=120s

echo "Deploying qdrant"
helm upgrade --install qdrant qdrant/qdrant -f k8s/values/qdrant.yaml --wait

echo "Deploying seaweed"
helm upgrade --install seaweedfs seaweedfs/seaweedfs -f k8s/values/seaweedfs.yaml --wait

echo "Infrastructure is Ready.