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

- **ProcureIntel HTML dashboard (primary)** runs locally on `http://127.0.0.1:8765` (see [Run ProcureIntel](#run-procureintel-primary-dashboard))
- Next.js API runs locally on `http://127.0.0.1:3000`
- Streamlit dashboard (legacy, optional) runs locally on `http://127.0.0.1:8501`
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

There are three demo surfaces (all non-destructive; shared Python logic where noted):

- **ProcureIntel HTML dashboard (primary)** under `monitor_site/`: FastAPI + HTML/CSS/JS, shares `monitor_core.py` with Streamlit
- **Next.js API app** under `web/`: governance API, Bedrock explain, S3 export, Amplify deployment
- **Streamlit dashboard (legacy)** at repo root in `app.py`: kept as fallback; shows a banner pointing to ProcureIntel

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

The ProcureIntel HTML dashboard connects to the **Agency 2026 unified Postgres warehouse** (~23M rows across CRA, FED, AB, and `general` entity matching). See the [GovAlta/agency-26-hackathon](https://github.com/GovAlta/agency-26-hackathon) repo for schema docs and `KNOWN-DATA-ISSUES.md`.

```text
DB_CONNECTION_STRING=<postgres connection string from hackathon organizers>
# or
DATABASE_URL=<same>
PGSSLMODE=prefer
GROQ_API_KEY=<optional, enables Ask ProcureIntel chatbot>
```

ProcureIntel **never loads full tables into memory**. It runs SQL aggregations per data lane and returns top-N ranked rows only.

Copy `.env.example` to `.env` at the repo root. Do not commit real database credentials.

---

## Run ProcureIntel (Primary Dashboard)

This is the recommended **Public Contract Change Monitor** interface: static HTML/CSS with Vega-Lite charts, governance console, multi-lane warehouse access, and optional Groq chatbot. It uses `monitor_data_platform.py`, `monitor_dashboard.py`, `monitor_charts.py`, and `monitor_core.py` (shared with Streamlit).

From the repository root that contains `app.py`:

```bash
cd Oil-City-Hackers-AI-Agency-26
python3 -m pip install -r requirements.txt
cp .env.example .env   # edit .env if you use Postgres
python3 -m uvicorn monitor_site.server:app --reload --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

Endpoints:

- `GET /`: dashboard UI (static assets under `/static/`)
- `GET /api/health`: warehouse connectivity and row estimates
- `GET /api/data/census`: per-schema row estimates (~23M total) and lane availability
- `GET /api/data/lanes`: data lane catalog (contracts, fed, ab, cra, entities)
- `GET /api/bootstrap`: filter option lists for the default contracts lane
- `GET /api/dashboard`: query params `dataset`, `min_original`, `department`, `procedure`, `selected_ref` (optional)
- `GET /api/chat/status`: whether the Groq chatbot is enabled (`{"enabled": true|false}`)
- `POST /api/chat`: Groq-backed Q&A over the active lane (see "Ask ProcureIntel" below)

**Data lanes** (`dataset` query param):

| Lane | Source | What it measures |
|------|--------|------------------|
| `contracts` | `public.contracts` | Federal amendment creep (~27K filtered candidates) |
| `fed` | `fed.vw_agreement_current` vs originals | Grant agreement growth (1.3M agreements, safe views) |
| `ab` | `ab.ab_sole_source` + `ab.ab_contracts` | Alberta non-competitive growth proxy |
| `cra` | `cra.govt_funding_by_charity` | Charity government funding intensity |
| `entities` | `general.vw_entity_funding` | Cross-dataset linked organizations |

The FastAPI app reads **`DB_CONNECTION_STRING`** or **`DATABASE_URL`** from the environment (plus optional **`PGSSLMODE`**, default **`prefer`**). It also loads `web/.env` if present.

Smoke checks:

```text
http://127.0.0.1:8765/api/health
http://127.0.0.1:8765/api/bootstrap
http://127.0.0.1:8765/api/dashboard?min_original=10000
```

Data behavior:

- Primary: SQL aggregations against the Agency 2026 warehouse (top 500 ranked rows per request)
- The **contracts** lane matches the Challenge 4 amendment-creep cohort (~27K rows after filters), not the full 23M table
- Other lanes surface federal grants, Alberta sole-source patterns, CRA funding, and cross-linked entities
- Without a DB URL, the dashboard cannot query the warehouse (a small `data/contracts.csv` sample exists for legacy Streamlit only)

### Ask ProcureIntel (Groq chatbot)

The dashboard includes an optional natural-language assistant. When a `GROQ_API_KEY` is configured, an **Ask ProcureIntel** button appears in the bottom-right of the dashboard. Users can ask questions like:

- *Which departments have the most flagged contracts?*
- *Summarize the top 5 highest amendment-ratio contracts.*
- *What is the median amendment ratio in the current scope?*

How it works:

1. Each request takes the current filters (`dataset`, `min_original`, `department`, `procedure`) and a SQL-backed summary of that lane.
2. The server builds a compact summary of the in-scope dataset (KPIs, top departments, top contracts by amendment ratio).
3. That summary is injected as a system prompt into a Groq chat completion. The model is instructed to answer **only** from the provided context, avoid accusatory language, and never use the word "fraud".

Setup:

1. Create a free API key at <https://console.groq.com>.
2. Add it to `.env` at the repo root:

   ```text
   GROQ_API_KEY=gsk_...
   # Optional override; defaults to llama-3.1-8b-instant
   GROQ_MODEL=llama-3.1-8b-instant
   ```

   If chat fails with `SSL: CERTIFICATE_VERIFY_FAILED` (common on macOS Python), run `pip install -r requirements.txt` so `certifi` is installed; the server uses it for Groq HTTPS. You can also set `SSL_CERT_FILE` to a PEM bundle, or as a last resort only `GROQ_SSL_VERIFY=0` (disables TLS verification).

3. Restart `uvicorn`. The chat button will only appear when the key is present.

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

## Run The Streamlit Dashboard (Legacy / Optional)

The Streamlit app remains available as a fallback. It shares the same Python data layer as ProcureIntel and displays a banner pointing users to the HTML dashboard.

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

### ProcureIntel (monitor_site)

Deploy the HTML dashboard independently from the Next.js Amplify app. A Dockerfile and Render blueprint are included at the repo root.

**Docker (local or any host):**

```bash
docker build -t procureintel .
docker run -p 8765:8765 --env-file .env procureintel
```

**Render:** connect the repo and use `render.yaml` (Docker web service on port 8765). Set `DATABASE_URL`, `GROQ_API_KEY`, and other env vars in the Render dashboard.

This does not affect the existing Amplify deployment of `web/`.

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

1. Open ProcureIntel at `http://127.0.0.1:8765` (or the Next.js API landing page at `:3000`).
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
