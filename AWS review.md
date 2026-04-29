For this challenge, I’d keep the stack ruthlessly simple: **SQL-first analytics on the existing Postgres dataset, a thin TypeScript web app on top, and Bedrock only for explanations, not for core detection**.

Because this is a **one-day hackathon on April 29, 2026 with code freeze at 2:00 PM**, the winning move is not “most AWS.” It’s “fastest path to credible findings.” The repo already gives you a shared PostgreSQL model with `ab.ab_contracts`, `ab.ab_sole_source`, and the `general` entity-resolution layer, so I would build on that instead of replatforming the data.

**Recommended stack**

**Backend / Data**
- **Source of truth:** existing shared PostgreSQL/Render database from the hackathon repo.
- **App backend:** **Next.js route handlers** or a small **Express/Fastify** API in TypeScript.
- **Analytics layer:** SQL views/materialized views in Postgres for the heavy lifting.
- **AWS use:**
  - **Bedrock Claude Sonnet 4.6** for “explain this flagged case” summaries.
  - **S3** for exporting scored cases / cached JSON snapshots.
  - **Amplify** for quick frontend hosting.
  - Optional: **Lambda** only for scheduled refresh/export jobs.

I would **not** use DynamoDB, Neptune, Kendra, SageMaker, AgentCore, or Step Functions for the core MVP. They add setup cost and don’t solve your main problem better than SQL.

**Why this fits challenge 4**
The Alberta schema is sparse:
- `ab.ab_contracts`: `recipient`, `amount`, `ministry`, `display_fiscal_year`
- `ab.ab_sole_source`: `vendor`, `amount`, `contract_number`, `contract_services`, `permitted_situations`, `start_date`, `end_date`, `ministry`, `display_fiscal_year`

That means you probably **do not have an explicit amendment chain**. So your product should frame results as:
- **probable follow-on sole-source patterns**
- **threshold splitting signals**
- **repeat vendor/ministry dependence**
- **competitive-to-sole-source creep risk**

That is much more defensible than pretending you can prove exact amendment lineage everywhere.

**Analytics design**
Build 4-5 materialized views:

1. `vendor_normalized`
- Normalize `recipient` and `vendor`
- Join to `general` golden records where possible
- Fallback to uppercase/trim/trigram matching

2. `contract_families`
- Group likely related records by normalized vendor + ministry + similar service text + time window
- Treat as “probable procurement family”

3. `threshold_signals`
- Flag clusters of contracts just under likely competition thresholds
- Show repeated near-threshold awards to same vendor/ministry

4. `vendor_rollups`
- Total competitive contract value
- Total sole-source value
- Sole-source share
- Count of years active
- Count of ministries
- Repeat-contract density

5. `risk_scored_cases`
- Composite score from:
  - sole-source follow-on amount / original competitive amount
  - number of sole-source follow-ons
  - near-threshold clustering
  - vendor concentration within ministry
  - repeated awards over multiple years
  - weak/strong linkage confidence

Use **Bedrock** only after scoring:
- Generate 2-3 sentence summaries for top flagged vendors/cases
- Explain why something was flagged in plain English
- Do not let the LLM decide the score

**Frontend**
I’d use:
- **Next.js**
- **Tailwind**
- **TanStack Table**
- **Apache ECharts**

Why ECharts instead of Recharts:
- Better for scatterplots, heatmaps, timelines, and denser analytic visuals
- More flexible if you want one standout chart for judges

**Core screens**
- **Ranked Cases**: sortable table of top flagged vendors/procurement families
- **Vendor Dossier**: all contracts, sole-source awards, ministries, years, risk factors
- **Ministry View**: concentration and threshold-splitting patterns by ministry
- **Methodology**: one page explaining scoring, caveats, and confidence levels

**Best charts**
- **Scatter plot:** original competitive value vs later sole-source total
- **Threshold cliff histogram:** contracts clustered just below threshold bands
- **Stacked bars:** competitive vs sole-source totals by vendor or ministry
- **Timeline:** awards to one vendor across years, colored by contract type
- **Pareto chart:** top vendors by sole-source share
- **Heatmap:** vendor vs ministry repeat relationships

If you have time for one “judge bait” chart, make it the **scatter plot of original value vs follow-on sole-source value**, with bubble size = total dollars and color = risk score.

**Practical build plan**
1. Build SQL views and produce a scored JSON/API output.
2. Ship one strong dashboard with a ranked table + vendor drilldown.
3. Add Bedrock summaries for the top 10 cases.
4. Only then add polish or extra charts.

If you want, I can turn this into a concrete repo plan next: folder structure, API endpoints, SQL view definitions, and the exact MVP screens.

References: [Luma event page](https://luma.com/5e83iia8), [GovAlta hackathon repo](https://github.com/GovAlta/agency-26-hackathon), [repo README raw](https://raw.githubusercontent.com/GovAlta/agency-26-hackathon/main/README.md), [AB schema raw](https://raw.githubusercontent.com/GovAlta/agency-26-hackathon/main/.local-db/schemas/ab.sql)