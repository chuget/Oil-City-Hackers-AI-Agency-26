# Agency 2026 – Team Handoff Brief

## Recommended Primary Build
**Sole Source and Amendment Creep**

## Why this is the best bet
- Fastest path to a credible working prototype
- Clear accountability story judges will understand immediately
- Mostly structured data and deterministic logic
- Strong visual demo potential without needing heavy ML

## Problem
Some contracts start as competitive procurements, then quietly grow through amendments or follow-on sole-source work until the final spend is far beyond the original justification.

## Why it matters
- Reduces transparency
- Can weaken competition
- Can hide vendor dependency
- Makes it harder to tell whether taxpayers got fair value

## MVP
Build a tool that:
1. Links original contracts to their amendments
2. Calculates growth from original value to final value
3. Flags contracts with unusually large amendment creep
4. Shows a ranked dashboard plus a contract drill-down view

## Core features
- Contract lineage view
- Original vs final value comparison
- Amendment count and growth multiple
- Risk flags for large expansion patterns
- Optional threshold-splitting view if time allows

## Data needed
- Contract award data
- Amendment data
- Vendor names/IDs
- Department or buyer information
- Commodity/category fields if available

## Suggested tech stack
- **Backend/data:** Python + DuckDB or Postgres
- **Analytics:** Pandas or Polars
- **Frontend:** Streamlit
- **Charts:** Plotly

## Demo flow
1. Start on a ranked list of contracts with the biggest amendment growth
2. Click one example contract
3. Show original award amount, amendment history, and final total
4. Highlight why it was flagged
5. Close with a summary of which departments/vendors/categories show the strongest pattern

## Judging angle
- Easy to understand in under 30 seconds
- Feels practical and immediately useful to government
- Connects AI/data tools to a real accountability outcome
- Can expand later into procurement oversight and audit workflows

## Stretch goal
Add a **Threshold Split Detector** to surface clusters of near-duplicate contracts just below competitive thresholds.

---

## Backup Option 1
**Vendor Concentration**

### Why pick it
- Very buildable in one day
- Clean dashboard story
- Low ambiguity and strong visuals

### MVP
Show concentration by category/department/region using HHI and top-vendor share.

### Best demo
Move across categories and show where government is overly dependent on a small supplier set.

---

## Backup Option 2
**Zombie Recipients**

### Why pick it
- Strongest emotional/accountability story
- Memorable demo if entity matching works
- Good judge appeal

### MVP
Show recipients that got public funding and then dissolved, went inactive, or stopped filing within 12 months.

### Best demo
Entity timeline with funding event, shutdown event, and supporting evidence.

---

## Team roles suggestion
- **Person 1:** data ingestion + cleanup
- **Person 2:** analytics/scoring logic
- **Person 3:** dashboard/demo UX
- **Person 4 (optional):** narrative, slides, and polish

## 1-Day execution plan
### Morning
- Load datasets
- Normalize contract IDs/vendors
- Build amendment linkage

### Midday
- Calculate risk metrics
- Build ranked table and detail view

### Afternoon
- Add charts and filters
- Pick 2-3 strong example cases
- Rehearse demo and tighten narrative

## Final recommendation
If the goal is to show up with something solid, credible, and easy to judge, go with **Sole Source and Amendment Creep**.
