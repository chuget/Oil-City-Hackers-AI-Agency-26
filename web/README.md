# Oil City Hackers API

Next.js/TypeScript API app for ranked contract cases, governance findings, optional Bedrock explanations, and optional S3 exports.

## Run

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

On Windows PowerShell, if script execution blocks npm shims, run:

```powershell
.\node_modules\.bin\next.cmd dev --hostname 127.0.0.1 --port 3000
```

## Environment

Copy `.env.example` to `.env.local`.

```text
DATABASE_URL=
CASE_DATASET=mock
AWS_DEFAULT_REGION=us-west-2
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
BEDROCK_MODEL_ID=
CASE_EXPORT_BUCKET=
```

`CASE_DATASET` supports:

- `mock`: fixture data for local integration
- `alberta`: live Alberta candidate query
- `federal`: legacy `public.contracts` candidate query

Do not commit real database or AWS credentials.

## API Endpoints

```text
GET  /api/health
GET  /api/db/schema
GET  /api/cases
GET  /api/cases/:reference_number
POST /api/govern
POST /api/explain
POST /api/exports/cases
```

## Governance

`POST /api/govern` is wired to the full Dev 3 governance implementation in:

```text
src/lib/governance.ts
```

It runs AG-01 through AG-09 and returns:

- `claim_state`
- `gates`
- `evidence`
- `data_gaps`
- `pc_rules_applied`
- `bounded_output_card`
- `flight_recorder`
- `next_step`

Example request:

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

Response:

```json
{
  "ok": true,
  "finding": {
    "claim_state": "INVESTIGATED",
    "gates": []
  }
}
```

## AWS

Amplify hosting uses the root `amplify.yml` build spec and the `web/` app root.

Bedrock is optional and explanation-only:

```text
POST /api/explain
Body: { "finding": GovernedFinding }
Returns: { "ok": true, "summary": "..." }
```

S3 exports are optional:

```text
POST /api/exports/cases
Body: { "limit": 50 }
Returns: { "ok": true, "destination": { "bucket": "...", "key": "..." } }
```

Set `CASE_EXPORT_BUCKET` to an existing S3 bucket before using the export route.

## Checks

```powershell
.\node_modules\.bin\eslint.cmd .
.\node_modules\.bin\next.cmd build
```
