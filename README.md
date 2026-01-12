# Asynchronous RAG Ingestion Platform

An event-driven RAG pipeline designed for high-throughput document ingestion on edge infrastructure (Oracle ARM).

This project demonstrates Platform Engineering principles: asynchronous processing, idempotent data handling, and infrastructure-as-code (IaC).


| Component       | Technology        | Role                  |
|-----------------|-------------------|-----------------------|
| Language        | 	Python 3.12	     | Ingestion Logic       |
| Package Manager | 	uv	              | Dependency Management |
| Queue           | 	RabbitMQ         | 	Task Broker          |
| Storage         | 	SeaweedFS        | 	Object Storage (S3)  |
| Vector DB       | Qdrant	           | Embedding Storage     |
| Container       | 	Docker           | 	Runtime Environment  |
| Orchestrator    | 	Kubernetes (K3s) | 	Cloud Deployment     |


# Architecture

```mermaid
graph TD
    %% Nodes
    Client[User / Python Script]
    
    subgraph "Oracle Cloud Kubernetes Cluster"
        Ingress[Traefik Ingress <br/> Basic Auth]
        
        subgraph "Data Plane"
            S3[SeaweedFS <br/> S3 Compatible]
            MQ[RabbitMQ]
        end
        
        subgraph "Compute Plane"
            Worker[Python Async Worker]
        end
        
        subgraph "Vector Database"
            Qdrant[Qdrant]
        end
    end

    %% Flows
    Client -- "1. Upload File (HTTPS)" --> Ingress
    Ingress --> S3
    
    Client -- "2. Publish Event (AMQP/HTTPS)" --> Ingress
    Ingress --> MQ
    
    MQ -- "3. Consume Task" --> Worker
    Worker -- "4. Download File (Internal)" --> S3
    Worker -- "5. Upsert Vectors" --> Qdrant

    %% Styling
    classDef storage fill:#f27f,stroke:#333,stroke-width:2px;
    classDef compute fill:#b3f,stroke:#333,stroke-width:2px;
    classDef net fill:#13f,stroke:#333,stroke-width:2px;
    
    class S3,MQ,Qdrant storage;
    class Worker compute;
    class Ingress net;
```

# Roadmap

- Observability with Prometheus
- Deployment automation
- Autoscaling with KEDA