# Oil City Hackers - Agency 2026

## Challenge 4: Sole Source & Amendment Creep

AI for Accountability Hackathon | April 29, 2026 | Ottawa

---

## What We Built

Oil City Hackers built a two-layer procurement accountability system:

1. **Detection layer**: surfaces contract candidates where amendment or follow-on value significantly exceeds the original award.
2. **Governance layer**: evaluates each candidate through a deterministic gate sequence and determines what the system is permitted to claim.

The core principle:

> Agents propose. Gates decide. Pattern is not verdict.

Detection answers: **what looks unusual?**

Governance answers: **what are we allowed to say about it, and what evidence is needed next?**

---

## Current Status

Verified locally on April 29, 2026:

- Next.js API runs locally on `http://127.0.0.1:3000`
- Streamlit dashboard runs locally on `http://127.0.0.1:8501`
- Live database connection works
- `/api/cases` returns live ranked cases
- `/api/govern` returns full governed findings
- `/api/explain` returns Bedrock-generated explanation summaries when AWS env vars are present
- `/api/exports/cases` exports cases to S3 when `CASE_EXPORT_BUCKET` is configured
- Governance layer AG-01 through AG-09 is implemented and merged

---

## Team Roles

| Member | Handle | Role |
|---|---|---|
| Regis Nde Tene | Kingtsugi | Governance logic, architecture, demo narrative |
| chuget | chuget | Backend API, TypeScript scaffold, deployment |
| Yunus Said | nullPtr | Streamlit dashboard and frontend UX |
| Adnan Jasim | ToxicChunk | Data, SQL, live database integration |
| Dave Panter | method.1 | Infrastructure and AWS support |

---

## Architecture

```text
Postgres / TRACE data
        |
        v
Candidate query / ranked cases
        |
        v
GET /api/cases
        |
        v
POST /api/govern
        |
        v
GovernedFinding
  - claim_state
  - AG-01 through AG-09 gate verdicts
  - evidence
  - data gaps
  - PC rules applied
  - bounded finding card
  - flight recorder
        |
        v
Dashboard / demo interface
```

There are two demo surfaces:

- **Next.js API app** under `web/`
- **Streamlit dashboard** at repo root in `app.py`

---

## Governance Layer

The canonical governance implementation is:

```text
web/src/lib/governance.ts
```

It is exposed through:

```text
POST /api/govern
```

Request shape:

```json
{
  "contract": {
    "reference_number": "DEMO-INV-001",
    "vendor_name": "Example Vendor Inc.",
    "department": "Public Services and Procurement Canada",
    "description": "IT services contract with amendment growth.",
    "contract_date": "2022-03-15",
    "original_value": 100000,
    "amendment_value": 100000,
    "current_value": 200000,
    "amendment_ratio": 1.0,
    "solicitation_procedure": "Non-competitive"
  }
}
```

Response shape:

```json
{
  "ok": true,
  "finding": {
    "claim_state": "INVESTIGATED",
    "gates": [],
    "evidence": [],
    "data_gaps": [],
    "pc_rules_applied": [],
    "headline": "...",
    "what_we_found": "...",
    "what_we_did_not_find": "...",
    "next_step": "...",
    "bounded_output_card": "...",
    "flight_recorder": []
  }
}
```

### Gate Sequence

| Gate | Name | Purpose |
|---|---|---|
| AG-01 | Evidence Provenance | Confirms source fields are present and traceable |
| AG-02 | Identity Resolution | Handles vendor identity and BN availability |
| AG-03 | Claim Strength (PRIMARY) | Matches claim level to evidence strength |
| AG-04 | Harm Boundary | Prevents harmful premature escalation |
| AG-05 | Temporal Window | Checks whether timing supports the pattern |
| AG-06 | Program / Policy Coherence | Screens structural explanations |
| AG-07 | Escalation Authority | Keeps Tier 3 escalation pending |
| AG-08 | Audit Completeness | Confirms gate chain is replayable |
| AG-09 | Public Defensibility | Prevents public-facing overclaiming |

### Claim States

- `CLEARED`: below threshold or no claim warranted
- `FLAGGED`: pattern detected, single signal
- `INVESTIGATED`: stronger signal or corroborated indicators, human review warranted
- `CRITICAL`: prohibited at Tier 3 and capped below external audit confirmation

### PC Rules

- **PC-01**: Pattern is not verdict
- **PC-02**: Missingness is not guilt
- **PC-03**: Claim strength matches evidence strength
- **PC-04**: No harmful escalation without named authority
- **PC-05**: Thresholds must be documented
- **PC-10**: No misconduct conclusion from open contract data alone
- **PC-12**: Use canonical current values; avoid unsafe raw summations

---

## Environment Variables

Do not commit real credentials.

The downloaded hackathon env file can be copied locally as:

```powershell
Copy-Item "C:\Users\regis\Downloads\env.download" ".\web\.env.local"
```

The Next.js app expects:

```text
DATABASE_URL=<postgres connection string>
CASE_DATASET=alberta
AWS_DEFAULT_REGION=<aws region>
AWS_ACCESS_KEY_ID=<aws access key>
AWS_SECRET_ACCESS_KEY=<aws secret>
AWS_SESSION_TOKEN=<aws session token>
BEDROCK_MODEL_ID=<bedrock model id>
CASE_EXPORT_BUCKET=<s3 bucket name>
```

`CASE_DATASET` supports:

- `mock`: local fixture data
- `alberta`: live Alberta candidate query
- `federal`: legacy federal/public contracts path

The Streamlit app expects:

```text
DB_CONNECTION_STRING=<postgres connection string>
```

If using the downloaded env file, map:

```text
DB_CONNECTION_STRING = DATABASE_URL
```

---

## Run The Next.js API App

```powershell
cd "C:\Users\regis\OneDrive\Documents\02_Projects\06_SPA\Agency 2026\Github\Oil-City-Hackers-AI-Agency-26\web"
npm install
.\node_modules\.bin\next.cmd dev --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

Smoke tests:

```text
http://127.0.0.1:3000/api/health
http://127.0.0.1:3000/api/cases
```

Build check:

```powershell
.\node_modules\.bin\eslint.cmd .
.\node_modules\.bin\next.cmd build
```

---

## Run The Streamlit Dashboard

Use a Python runtime with `streamlit`, `pandas`, `altair`, and `psycopg`.

```powershell
cd "C:\Users\regis\OneDrive\Documents\02_Projects\06_SPA\Agency 2026\Github\Oil-City-Hackers-AI-Agency-26"
python -m pip install -r requirements.txt
$env:DB_CONNECTION_STRING = $env:DATABASE_URL
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

Data behavior:

- Primary: live Postgres query from `dev1-sql/DEV1_CANONICAL_SQL_CONTRACT.sql`
- Fallback: `data/contracts.csv` when `DB_CONNECTION_STRING` is not set

---

## API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | API and DB smoke test |
| `GET` | `/api/db/schema` | Schema/table probe |
| `GET` | `/api/cases` | Ranked contract candidates |
| `GET` | `/api/cases/:reference_number` | Single case detail |
| `POST` | `/api/govern` | Full AG-01 through AG-09 governance finding |
| `POST` | `/api/explain` | Optional Bedrock summary for a governed finding |
| `POST` | `/api/exports/cases` | Optional S3 export of cases |

---

## Deployment Notes

### AWS Amplify

The repository includes:

```text
amplify.yml
```

Amplify configuration:

- Repository: `chuget/Oil-City-Hackers-AI-Agency-26`
- Branch: `main`
- App root: `web`
- Build command: handled by `amplify.yml`
- Required env vars: same as the Next.js env section above

### Vercel Fallback

If Amplify auth or GitHub linking blocks deployment, Vercel can deploy the Next.js app quickly.

From `web/`:

```powershell
npx vercel --prod
```

Add environment variables in the Vercel project settings. Do not paste real secrets into chat or committed files.

---

## Demo Flow

1. Open the dashboard or API landing page.
2. Show `/api/health`: database connected, dataset configured.
3. Show `/api/cases`: ranked amendment or follow-on candidates.
4. Select one high-ratio case.
5. Run `/api/govern` or dashboard governance view.
6. Show:
   - claim state
   - gate verdicts
   - bounded finding card
   - evidence gaps
   - next step
7. Close with:

```text
Detection found the pattern.
Governance determined what we are permitted to say about it.
```

---

## Submission

Team: Oil City Hackers

Challenge: Challenge 4 - Sole Source & Amendment Creep

Event: Agency 2026 AI for Accountability Hackathon

Core differentiator: deterministic governance layer for defensible AI-assisted accountability findings.
