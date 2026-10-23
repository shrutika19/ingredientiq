# IngredientIQ

IngredientIQ helps people understand skincare product ingredient lists. The React frontend submits ingredient text to a FastAPI backend, which stores the submission in PostgreSQL and can request an ingredient analysis from Google Gemini. Analysis results are saved and can be retrieved later using the submission ID.

> **Note:** Ingredient insights are informational and are not medical advice. The application does not provide a scientific safety score.

## Features

- Responsive React, TypeScript, and Tailwind CSS landing page.
- Ingredient text submission through the backend API.
- Gemini-powered ingredient analysis, including an overall assessment, ingredient functions, cautions, and uncertainties.
- Persisted analysis results that can be reopened through the submission URL.
- FastAPI health and database readiness endpoints.
- Nginx API gateway with per-IP request throttling and PostgreSQL-backed daily analysis quotas.


## Project structure

```text
backend/
  Dockerfile
  app/
    api/          API routes
    core/         Configuration and exception handlers
    database/     Database engine and session dependencies
    models/       SQLAlchemy models
    schemas/      API request and response schemas
    services/     Submission and analysis services
    alembic/      Database migrations
  tests/
  alembic.ini
  requirements.txt
gateway/
  nginx.conf       Nginx reverse proxy and edge rate limits
docker-compose.yml  API and gateway deployment
frontend/
  src/
    api/          Backend API clients
    components/   React page components
    types/        TypeScript API types
```

## Requirements

- Python 3.12
- Node.js 22 and npm
- PostgreSQL
- A Google Gemini API key for live ingredient analysis

## Local setup

### 1. Configure the backend

In PowerShell, create a virtual environment and install the backend requirements:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env` and set the PostgreSQL connection values and Gemini key:

```dotenv
APP_ENV=development
DEBUG=false
FRONTEND_ORIGINS=["http://localhost:5173"]

DB_HOST=localhost
DB_PORT=5432
DB_NAME=ingredientiq_db
DB_USER=ingredientiq_user
DB_PASSWORD=replace_with_your_local_password

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_available_gemini_model
GEMINI_TIMEOUT_SECONDS=30
```

Create the configured PostgreSQL database and user before starting the API. Keep real credentials in local environment files or a secret manager; do not commit them.

Apply migrations and start the backend from the `backend` directory:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs` when the app is not running in production mode.

### API gateway, rate limits, and daily quota

For a containerized deployment, copy the root `.env.example` to `.env`, set the database connection, Gemini key, frontend origin, and a random `API_LIMIT_HASH_SECRET` (at least 32 characters), then apply database migrations and start the API behind the Nginx gateway:

```powershell
Copy-Item .env.example .env
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d
```

The gateway is published on port `8000` by default (`GATEWAY_PORT` changes it). Only the gateway publishes a host port; the API container is reachable on the private Compose network. Point the frontend's `VITE_API_BASE_URL` at the gateway origin. The configured PostgreSQL service must be reachable from the API container; for Docker Desktop, `host.docker.internal` can reach a database running on the host.

`POST /api/v1/submissions` and `POST /api/v1/submissions/{submission_id}/analyze` are limited to 10 requests per IP per minute at both Nginx and the API. Submissions are additionally capped at 100 per IP per UTC day (`API_DAILY_SUBMISSIONS_PER_IP`); analysis attempts remain capped at 5 per IP per UTC day (`API_DAILY_ANALYSES_PER_IP`). Submission and analysis quotas count requests before processing, including failed requests and analyses for invalid submission IDs. The counters are atomic and stored in PostgreSQL, so they are shared across API workers and survive restarts. IPv4 clients are keyed by individual address; IPv6 clients are grouped by /64 network, preventing address rotation within a subnet from bypassing the daily caps. Client network keys are stored only as keyed hashes; keep `API_LIMIT_HASH_SECRET` stable across replicas and deployments. Clients sharing a public/NAT IPv4 address or IPv6 /64 share its quota. API-generated `429 Too Many Requests` responses include a `Retry-After` header; Nginx also rejects excess traffic at the gateway with HTTP 429.

When running the API outside the provided Compose network, leave `TRUSTED_PROXY_IPS` empty unless it is behind a trusted reverse proxy. If a proxy is used, configure the API to trust only that proxy's IP/CIDR and configure it to overwrite `X-Real-IP` with the actual client address. Do not expose the API container directly to the public internet or trust arbitrary forwarded headers. Configure HTTPS termination at the public edge in production. If a separate load balancer or TLS proxy sits in front of Nginx, configure Nginx's real-IP module to trust only that upstream's IP/CIDR; otherwise Nginx will see and rate-limit the upstream proxy's address.

### 2. Configure and start the frontend

In a second PowerShell window:

```powershell
cd frontend
npm ci
npm run dev
```

Open the Vite URL shown in the terminal (by default, `http://localhost:5173`). The frontend defaults to the backend at `http://localhost:8000`. To use a different API URL, create `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## API endpoints

All API endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Check that the API is running. |
| `GET` | `/health/ready` | Check database connectivity and that Alembic migrations are at head. |
| `POST` | `/submissions` | Save ingredient text and return a submission ID. |
| `POST` | `/submissions/{submission_id}/analyze` | Queue analysis and return `202 Accepted` with its pending analysis ID. |
| `GET` | `/submissions/{submission_id}/analysis` | Retrieve the latest saved analysis for a submission. |

Example submission body:

```json
{
  "ingredient_text": "Aqua, Glycerin, Niacinamide"
}
```

Ingredient text must contain 3–10,000 characters. The analysis request is made by the backend; the browser never receives or uses the Gemini API key.

API errors use a consistent envelope: `{"error":{"code":"...","message":"..."}}`. Readiness returns HTTP 503 when the database is unavailable or its Alembic revision does not match the code's current migration head.

Analysis requests are processed in a FastAPI background task using a separate database session. The response is returned immediately with `202 Accepted`; clients can poll the `Location` URL (or the `GET` endpoint above) until the status becomes `COMPLETED` or `FAILED`. Background tasks are in-process and are not durable across API process crashes; stale active analyses are failed by the existing retry-time sweep, while a dedicated worker queue remains a future scaling step.

Retrieval caches successful canonical-ingredient query embeddings in a bounded per-process LRU cache (512 entries, keyed by embedding model, dimensions, and query text), reducing repeated embedding API calls for common ingredients. Evidence context is bounded to 20 snippets, with one top-ranked snippet requested per resolved ingredient, allowing evidence retrieval to cover up to 20 ingredients per analysis while keeping prompt size bounded. Each API process has its own embedding cache.

For supported ingredient findings, the model returns a short verbatim `supporting_quote`; the API verifies that quote appears in a cited evidence excerpt. The explanation may paraphrase the excerpt. Findings without a matching quote are downgraded to limited support.

## Tests and checks

Run backend tests from the `backend` directory:

```powershell
python -m pytest -q -m "not integration"
```

The standard backend test selection excludes tests marked `integration`. Those tests make live requests to Gemini and require `GEMINI_API_KEY`:

```powershell
python -m pytest -q -m integration
```

Run frontend checks from `frontend`:

```powershell
npm run lint
npm run build
```

The GitHub Actions CI workflow runs the frontend checks and backend tests excluding live Gemini integration tests, so CI does not require a Gemini secret.
