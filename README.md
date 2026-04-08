# AI Content Processing Pipeline

Async multi-tenant text ingestion pipeline. Takes raw text (job/internship postings), queues it for processing, extracts structured data via LLMs, validates output through layered checks, and stores results with full status tracking.

## Why this domain

I built a similar ingestion pipeline in production for a job aggregation platform. That system was admin-only, single-tenant, with OCR support for screenshots. For this assignment I stripped the OCR layer (adds complexity without demonstrating system design), kept the extraction core, and redesigned it for multi-user concurrency with proper queueing, rate limiting, and fault tolerance.

## Architecture

### Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Redis
    participant Celery Worker
    participant LLM
    participant SQLite

    Client->>FastAPI: POST /api/ingest (X-API-Key)
    FastAPI->>SQLite: lookup API key
    FastAPI->>Redis: check rate limit (sliding window)
    FastAPI->>SQLite: check idempotency key
    FastAPI->>SQLite: create submission (status: queued)
    FastAPI->>Redis: dispatch task to queue
    FastAPI-->>Client: 202 Accepted {submission_id}

    Celery Worker->>Redis: pick up task
    Celery Worker->>SQLite: update status -> processing
    Celery Worker->>LLM: extract structured data
    LLM-->>Celery Worker: JSON response
    Celery Worker->>Celery Worker: validate (schema + rules)
    Celery Worker->>SQLite: store result, status -> completed

    Client->>FastAPI: GET /api/status/{id}
    FastAPI->>SQLite: fetch submission
    FastAPI-->>Client: {status, result, provider, ...}
```

### System Components

```mermaid
graph TB
    subgraph API Layer
        A[FastAPI Server] --> B[Auth: API Key Lookup]
        B --> C[Rate Limiter: Redis Sliding Window]
        C --> D[Input Validation + Idempotency Check]
    end

    subgraph Queue
        D --> E[Redis: Celery Broker]
    end

    subgraph Worker Layer
        E --> F[Celery Worker]
        F --> G[LLM Router]
        G --> H[Groq: Primary - Round Robin Keys]
        G --> I[Gemini: Fallback]
        H -.->|429/500| I
        F --> J[Validation: Pydantic + Business Rules]
    end

    subgraph Storage
        K[(SQLite)]
    end

    subgraph Reliability
        L[Circuit Breaker per Groq Key]
        M[Exponential Backoff Retries]
        N[DLQ: failed status in DB]
    end

    F --> K
    A --> K
```

### Data Model

```mermaid
erDiagram
    API_KEYS {
        string key PK
        string user_id UK
        string tier
        datetime created_at
        int is_active
    }

    SUBMISSIONS {
        string id PK
        string user_id FK
        string idempotency_key
        text raw_text
        string status
        json result
        text error
        int retry_count
        string llm_provider
        datetime created_at
        datetime started_at
        datetime completed_at
    }

    API_KEYS ||--o{ SUBMISSIONS : "user_id"
```

### LLM Fallback Strategy

```mermaid
flowchart LR
    A[Incoming Text] --> B{Groq Key Available?}
    B -->|Yes| C[Call Groq]
    C -->|Success| D[Return Result]
    C -->|429| E[Trip Circuit, Try Next Key]
    E -->|Key Available| C
    E -->|All Tripped| F[Call Gemini]
    C -->|500/Timeout| G[Record Failure]
    G --> F
    B -->|No Keys / All Tripped| F
    F -->|Success| D
    F -->|Fail| H[Raise Error -> Celery Retry]
```

## Setup

### Prerequisites
- Python 3.11+
- Docker (for Redis)
- At least one LLM API key (Groq or Gemini)

### Run

```bash
# create venv and install
python -m venv venv
.\venv\Scripts\activate        # windows
# source venv/bin/activate     # linux/mac
pip install -r requirements.txt

# copy env and add your LLM keys
cp .env.example .env

# start redis
docker compose up -d

# seed test API keys
python test.py

# start the API (terminal 1)
uvicorn backend.main:app --reload --port 8000

# start the worker (terminal 2)
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

### Testing the LLM Independently

If you only want to verify the LLM extraction logic and fallback router without spinning up Redis, Celery, or the FastAPI web server, you can run the standalone test script:

```bash
python test_llm.py
```

## API Endpoints

### POST /api/ingest
Submit text for structured extraction. Returns immediately with a submission ID.

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-user-1" \
  -d '{
    "text": "Hiring at Google for SDE Intern, batch 2025, stipend 80000/month, Bangalore. Apply at careers.google.com",
    "idempotency_key": "unique-123"
  }'
```

Response: `202 Accepted`
```json
{"submission_id": "uuid", "status": "queued", "message": "submission queued for processing"}
```

### GET /api/status/{submission_id}
Poll for processing result.

```bash
curl http://localhost:8000/api/status/<submission_id> \
  -H "X-API-Key: test-key-user-1"
```

### GET /api/submissions
List all your submissions (most recent first, max 50).

```bash
curl http://localhost:8000/api/submissions \
  -H "X-API-Key: test-key-user-1"
```

### GET /health
Health check, no auth needed.

## Project Structure

```
backend/
  config.py        - env-based configuration
  db.py            - SQLAlchemy engine and session
  models.py        - Submission + ApiKey tables
  schemas.py       - Pydantic request/response/extraction models
  main.py          - FastAPI routes, auth, rate limiting
  celery_app.py    - Celery broker setup
  tasks.py         - background worker task
  llm.py           - LLM router with circuit breaker + fallback
  rate_limiter.py  - Redis sliding window rate limiter
  validation.py    - schema + rule-based output validation
test.py            - seeds test API keys into the DB
docker-compose.yml - Redis container
```
