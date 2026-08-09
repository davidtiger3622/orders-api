# orders-api

A FastAPI + PostgreSQL + Redis checkout microservice. Redis is used to
enforce idempotency on checkout requests via a short-lived lock, preventing
duplicate order creation when a client retries a request.

## Tech stack

- FastAPI
- PostgreSQL (via SQLAlchemy)
- Redis (idempotency locking)
- Docker Compose for local development

## Running locally

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start the stack:

```bash
   docker compose up --build
```

3. The API will be available at `http://localhost:8000`.
   Health check: `GET /health`.

## Endpoints

- `POST /orders/checkout` — creates an order. Requires an `idempotency_key`;
  retried requests with the same key return the original order instead of
  creating a duplicate.
- `GET /orders/{order_id}` — fetches an order by ID.

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Incident reports

See `incident/` for postmortem drafts related to production incidents.
