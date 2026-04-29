# Oil City Hackers API

Next.js/TypeScript scaffold for the Dev 2 API layer.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Environment

Copy `.env.example` to `.env.local`.

```bash
DATABASE_URL=
CASE_DATASET=mock
```

`CASE_DATASET` supports:

- `mock`: fixture data for frontend/governance integration
- `alberta`: `ab.ab_sole_source` + `ab.ab_contracts`
- `federal`: legacy `public.contracts` candidate query

Do not commit real database credentials.

## API Endpoints

```text
GET  /api/health
GET  /api/db/schema
GET  /api/cases
GET  /api/cases/:reference_number
POST /api/govern
```

`POST /api/govern` accepts:

```json
{
  "contract": {
    "reference_number": "DEMO-INV-001",
    "vendor_name": "Northstar Systems Inc.",
    "department": "Public Services and Procurement Canada",
    "description": "IT professional services contract with major amendment growth.",
    "contract_date": "2024-02-15",
    "original_value": 125000,
    "amendment_value": 285000,
    "current_value": 410000,
    "amendment_ratio": 2.28,
    "solicitation_procedure": "Non-competitive",
    "bn": "123456789"
  }
}
```

It returns `{ "ok": true, "finding": GovernedFinding }`.

## Dev 3 Handoff

Replace `src/lib/governance.ts` with the full AG-01 through AG-09 implementation when ready. The route already imports `governContract(contract)`.

## Dev 4 Handoff

Use `/api/cases` for the ranked table and `/api/govern` for the governed finding card. Mock cases are available immediately without a database.
