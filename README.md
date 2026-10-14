# IngredientIQ

IngredientIQ helps people understand skincare product ingredient lists. The React frontend submits ingredient text to a FastAPI backend, which stores the submission in PostgreSQL and can request an ingredient analysis from Google Gemini. Analysis results are saved and can be retrieved later using the submission ID.

> **Note:** Ingredient insights are informational and are not medical advice. The application does not provide a scientific safety score.

## Features

- Responsive React, TypeScript, and Tailwind CSS landing page.
- Ingredient text submission through the backend API.
- Gemini-powered ingredient analysis, including an overall assessment, ingredient functions, cautions, and uncertainties.
- Persisted analysis results that can be reopened through the submission URL.
- FastAPI health and database readiness endpoints.


## Project structure

```text
backend/
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
| `GET` | `/health/ready` | Check API and database readiness. |
| `POST` | `/submissions` | Save ingredient text and return a submission ID. |
| `POST` | `/submissions/{submission_id}/analyze` | Analyze a saved submission using the backend Gemini service. |
| `GET` | `/submissions/{submission_id}/analysis` | Retrieve the latest saved analysis for a submission. |

Example submission body:

```json
{
  "ingredient_text": "Aqua, Glycerin, Niacinamide"
}
```

Ingredient text must contain 3–10,000 characters. The analysis request is made by the backend; the browser never receives or uses the Gemini API key.

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
