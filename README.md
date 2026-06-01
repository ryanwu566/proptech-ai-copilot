# PropGuard AI

PropGuard AI project skeleton.

This repository includes a local MVP workflow for property risk intake, deterministic rules-based analysis, HTML report rendering, and PDF export. It does not connect to real APIs or run AI/ML workflows.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui-style components
- Backend: FastAPI
- Services: PostgreSQL, Redis
- Runtime: Docker Compose

## Project Structure

```text
.
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── globals.css
│   │   ├── aegis-credit/
│   │   ├── lex-prop/
│   │   ├── tax-oracle/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   └── ui/
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       └── card.tsx
│   ├── lib/
│   │   └── utils.ts
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/health
- Aegis-Credit form: http://localhost:3000/aegis-credit
- TaxOracle form: http://localhost:3000/tax-oracle
- LexProp form: http://localhost:3000/lex-prop

## Health Check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "propguard-api",
  "environment": "development"
}
```

## Assessment API

The module endpoints store local PostgreSQL records and return deterministic rules-engine results:

- `POST /api/aegis-credit/assessments`
- `POST /api/tax-oracle/assessments`
- `POST /api/lex-prop/assessments`

Each saved assessment also has report endpoints:

- `GET /api/aegis-credit/assessments/{id}/report`
- `GET /api/aegis-credit/assessments/{id}/report.pdf`
- `GET /api/tax-oracle/assessments/{id}/report`
- `GET /api/tax-oracle/assessments/{id}/report.pdf`
- `GET /api/lex-prop/assessments/{id}/report`
- `GET /api/lex-prop/assessments/{id}/report.pdf`

Reports are rendered from an HTML template before PDF export.

## Data Ingestion Adapters

External source integration is prepared as replaceable adapters under `backend/app/data_ingestion/`.
The current implementations are mocks only and do not force-connect to external APIs:

- `real_price.py`: real-price transaction samples
- `judicial.py`: judicial case search references
- `legal.py`: legal reference lookup
- `cbc_policy.py`: central bank credit-policy references
- `bank_rates.py`: bank mortgage-rate references

Each adapter exposes an interface-style `Protocol`, a mock implementation, and a `source_log`
record that tracks source name, retrieval mode, query, status, record count, and request time.
