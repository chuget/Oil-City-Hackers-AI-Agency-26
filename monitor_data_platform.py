"""
Agency 2026 multi-lane data platform for ProcureIntel.

Queries the unified Postgres warehouse (~23M rows across CRA, FED, AB, general)
without loading full tables into memory. Each lane returns small aggregates and
top-N ranked rows only.
"""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from monitor_core import _pg_connect, db_config_present, _db_connection_string

DatasetLane = Literal["contracts", "fed", "ab", "cra", "entities"]

RANKED_LIMIT = 500

LANE_META: dict[str, dict[str, str]] = {
    "contracts": {
        "label": "Federal contracts (amendment creep)",
        "description": "public.contracts — amendment ratio vs original award (~27K candidates after filters).",
        "source_table": "public.contracts",
    },
    "fed": {
        "label": "Federal grants & contributions",
        "description": "fed.vw_agreement_current vs originals — growth in commitment (~1.3M agreements, SQL-safe views).",
        "source_table": "fed.grants_contributions",
    },
    "ab": {
        "label": "Alberta sole-source vs contracts",
        "description": "ab.ab_sole_source matched to ab.ab_contracts — non-competitive growth proxy (~2.6M AB rows).",
        "source_table": "ab.ab_sole_source",
    },
    "cra": {
        "label": "CRA charities — government funding",
        "description": "cra.govt_funding_by_charity — T3010 government funding intensity (~8.8M CRA filings).",
        "source_table": "cra.govt_funding_by_charity",
    },
    "entities": {
        "label": "Cross-dataset entities",
        "description": "general.vw_entity_funding — golden records linked across CRA, FED, and AB (~851K entities).",
        "source_table": "general.entities",
    },
}

CENSUS_SCHEMAS = ("cra", "fed", "ab", "general", "public")


def list_lanes() -> list[dict[str, str]]:
    return [{"id": k, **v} for k, v in LANE_META.items()]


def _query_df(conn, sql: str, params: dict | None = None) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        if not cur.description:
            return pd.DataFrame()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def _object_exists(conn, schema: str, name: str, kind: str = "table") -> bool:
    relkind = "r" if kind == "table" else "v"
    df = _query_df(
        conn,
        """
        SELECT 1 AS ok
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %(schema)s AND c.relname = %(name)s AND c.relkind = %(kind)s
        LIMIT 1
        """,
        {"schema": schema, "name": name, "kind": relkind},
    )
    return not df.empty


def lane_available(conn, lane: DatasetLane) -> bool:
    meta = LANE_META.get(lane, {})
    table = meta.get("source_table", "")
    if "." not in table:
        return False
    schema, rel = table.split(".", 1)
    if not _object_exists(conn, schema, rel, "table"):
        return False
    if lane == "fed":
        return _object_exists(conn, "fed", "vw_agreement_current", "view") and _object_exists(
            conn, "fed", "vw_agreement_originals", "view"
        )
    if lane == "entities":
        return _object_exists(conn, "general", "vw_entity_funding", "view")
    return True


def get_data_census() -> dict[str, Any]:
    """Row estimates per schema from pg_stat (fast on large DBs)."""
    if not db_config_present():
        return {
            "ok": False,
            "message": "Set DB_CONNECTION_STRING or DATABASE_URL to connect to the Agency 2026 warehouse.",
            "total_estimate": 0,
            "schemas": [],
            "lanes": [{"id": k, "available": False, **v} for k, v in LANE_META.items()],
        }

    conn_str = _db_connection_string()
    with _pg_connect(conn_str) as conn:
        stats = _query_df(
            conn,
            """
            SELECT
              n.nspname AS schema,
              c.relname AS table_name,
              GREATEST(c.reltuples::bigint, 0) AS row_estimate
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = ANY(%(schemas)s)
              AND c.relkind = 'r'
            ORDER BY row_estimate DESC
            """,
            {"schemas": list(CENSUS_SCHEMAS)},
        )

        schema_totals: dict[str, int] = {}
        tables_out: list[dict[str, Any]] = []
        for _, row in stats.iterrows():
            est = int(row["row_estimate"] or 0)
            sch = str(row["schema"])
            schema_totals[sch] = schema_totals.get(sch, 0) + est
            if est >= 10_000:
                tables_out.append(
                    {
                        "schema": sch,
                        "table": str(row["table_name"]),
                        "row_estimate": est,
                    }
                )

        lanes_out = []
        for lane_id, meta in LANE_META.items():
            lanes_out.append(
                {
                    "id": lane_id,
                    "label": meta["label"],
                    "description": meta["description"],
                    "available": lane_available(conn, lane_id),  # type: ignore[arg-type]
                }
            )

    total = int(sum(schema_totals.values()))
    return {
        "ok": True,
        "total_estimate": total,
        "schema_totals": schema_totals,
        "top_tables": tables_out[:24],
        "lanes": lanes_out,
        "note": (
            "Estimates come from PostgreSQL table statistics (pg_class.reltuples). "
            "The hackathon warehouse unifies ~23M rows across CRA, FED, AB, and general. "
            "ProcureIntel never loads full tables; it runs SQL aggregations and returns top-N rows."
        ),
    }


def _empty_lane_payload(lane: str, message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "lane_unavailable",
        "dataset": lane,
        "dataset_label": LANE_META.get(lane, {}).get("label", lane),
        "message": message,
        "rows_in_lane": 0,
        "rows_returned_ranked": 0,
        "filter_departments": ["(all)"],
        "filter_procedures": ["(all)"],
        "kpis": {"contracts_scanned": 0, "ratio_gt_25": 0, "ratio_gt_100": 0, "ratio_gt_300": 0},
        "dept_rollup": [],
        "ranked": [],
    }


def _apply_dept_proc_filters(
    base_sql: str,
    department: str,
    procedure: str,
    dept_col: str = "department",
    proc_col: str = "solicitation_procedure",
) -> tuple[str, dict]:
    params: dict[str, Any] = {}
    clauses = []
    if department and department != "(all)":
        clauses.append(f"AND {dept_col} = %(department)s")
        params["department"] = department
    if procedure and procedure != "(all)":
        clauses.append(f"AND {proc_col} = %(procedure)s")
        params["procedure"] = procedure
    return base_sql + "\n".join(clauses), params


# ── Contracts lane (public.contracts) ─────────────────────────────────────────

CONTRACTS_SCORED_CTE = """
WITH typed AS (
  SELECT
    id,
    reference_number,
    procurement_id,
    reporting_period,
    vendor_name,
    owner_org_title AS department,
    contract_date,
    solicitation_procedure AS solicitation_procedure_raw,
    CASE solicitation_procedure
      WHEN 'OB' THEN 'Open bidding'
      WHEN 'TC' THEN 'Traditional competitive'
      WHEN 'TN' THEN 'Traditional non-competitive'
      WHEN 'AC' THEN 'Advance contract award notice'
      WHEN 'ST' THEN 'Standing offer or supply arrangement'
      ELSE COALESCE(solicitation_procedure, 'Unknown')
    END AS solicitation_procedure,
    CASE WHEN TRIM(original_value) ~ '^[0-9]+(\\.[0-9]+)?$'
         THEN TRIM(original_value)::numeric(15,2) END AS original_value,
    CASE WHEN TRIM(amendment_value) ~ '^[0-9]+(\\.[0-9]+)?$'
         THEN TRIM(amendment_value)::numeric(15,2) END AS amendment_value,
    CASE WHEN TRIM(contract_value) ~ '^[0-9]+(\\.[0-9]+)?$'
         THEN TRIM(contract_value)::numeric(15,2) END AS current_value,
    COALESCE(description_en, 'Not provided in canonical output.') AS description
  FROM public.contracts
),
scored AS (
  SELECT
    *,
    ROUND(((amendment_value / NULLIF(original_value, 0)) - 1)::numeric, 6) AS amendment_ratio
  FROM typed
  WHERE original_value > %(min_original)s
    AND amendment_value IS NOT NULL
    AND current_value IS NOT NULL
    AND amendment_value > 0
)
"""


def _lane_contracts_sql(
    conn,
    min_original: float,
    department: str,
    procedure: str,
    ranked_limit: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"min_original": float(min_original), "ranked_limit": int(ranked_limit)}

    kpis_sql = CONTRACTS_SCORED_CTE + """
SELECT
  COUNT(*)::bigint AS contracts_scanned,
  COUNT(*) FILTER (WHERE amendment_ratio > 0.25)::bigint AS ratio_gt_25,
  COUNT(*) FILTER (WHERE amendment_ratio > 1.0)::bigint AS ratio_gt_100,
  COUNT(*) FILTER (WHERE amendment_ratio > 3.0)::bigint AS ratio_gt_300
FROM scored
"""
    kpis_sql, fp = _apply_dept_proc_filters(kpis_sql, department, procedure)
    params.update(fp)
    kpis_row = _query_df(conn, kpis_sql, params).iloc[0].to_dict()

    dept_sql = CONTRACTS_SCORED_CTE + """
SELECT
  department,
  COUNT(*)::bigint AS contracts,
  COUNT(*) FILTER (WHERE amendment_ratio > 0.25)::bigint AS flagged,
  AVG(amendment_ratio)::float AS avg_ratio,
  MAX(amendment_ratio)::float AS max_ratio
FROM scored
WHERE 1=1
"""
    dept_sql, fp = _apply_dept_proc_filters(dept_sql, "", procedure)
    params.update(fp)
    dept_sql += """
GROUP BY department
ORDER BY flagged DESC, avg_ratio DESC NULLS LAST
LIMIT 10
"""
    dept_rollup = _query_df(conn, dept_sql, params)

    proc_sql = CONTRACTS_SCORED_CTE + """
SELECT solicitation_procedure, COUNT(*)::bigint AS contracts
FROM scored
WHERE 1=1
"""
    proc_sql, fp = _apply_dept_proc_filters(proc_sql, department, "")
    params.update(fp)
    proc_sql += """
GROUP BY solicitation_procedure
ORDER BY contracts DESC
LIMIT 10
"""
    proc_rollup = _query_df(conn, proc_sql, params)

    hist_sql = CONTRACTS_SCORED_CTE + """
SELECT
  (FLOOR(LEAST(amendment_ratio * 100.0, 400.0) / 25.0) * 25.0)::float AS bin_start,
  COUNT(*)::bigint AS contracts
FROM scored
WHERE 1=1
"""
    hist_sql, fp = _apply_dept_proc_filters(hist_sql, department, procedure)
    params.update(fp)
    hist_sql += " GROUP BY 1 ORDER BY 1"
    hist_df = _query_df(conn, hist_sql, params)
    if not hist_df.empty:
        hist_df["bin_end"] = hist_df["bin_start"] + 25.0

    filters_sql = CONTRACTS_SCORED_CTE + """
SELECT DISTINCT department, solicitation_procedure FROM scored
"""
    filters_df = _query_df(conn, filters_sql, {"min_original": float(min_original)})

    ranked_sql = CONTRACTS_SCORED_CTE + """
SELECT
  reference_number,
  vendor_name,
  department,
  original_value,
  amendment_value,
  current_value,
  (amendment_ratio * 100.0)::float AS ratio_pct,
  (amendment_ratio + 1.0)::float AS ratio_x,
  solicitation_procedure,
  procurement_id,
  contract_date,
  description
FROM scored
WHERE 1=1
"""
    ranked_sql, fp = _apply_dept_proc_filters(ranked_sql, department, procedure)
    params.update(fp)
    ranked_sql += " ORDER BY amendment_ratio DESC NULLS LAST LIMIT %(ranked_limit)s"
    ranked = _query_df(conn, ranked_sql, params)

    return {
        "kpis": {
            "contracts_scanned": int(kpis_row.get("contracts_scanned") or 0),
            "ratio_gt_25": int(kpis_row.get("ratio_gt_25") or 0),
            "ratio_gt_100": int(kpis_row.get("ratio_gt_100") or 0),
            "ratio_gt_300": int(kpis_row.get("ratio_gt_300") or 0),
        },
        "dept_rollup": dept_rollup,
        "proc_rollup": proc_rollup,
        "hist_df": hist_df,
        "ranked": ranked,
        "filter_departments": ["(all)"] + sorted(filters_df["department"].dropna().unique().tolist()),
        "filter_procedures": ["(all)"] + sorted(filters_df["solicitation_procedure"].dropna().unique().tolist()),
        "rows_in_lane": int(kpis_row.get("contracts_scanned") or 0),
    }


# ── FED lane ──────────────────────────────────────────────────────────────────

FED_SCORED_CTE = """
WITH paired AS (
  SELECT
    c.ref_number AS reference_number,
    c.recipient_legal_name AS vendor_name,
    c.owner_org_title AS department,
    o.agreement_value::numeric(15,2) AS original_value,
    (c.agreement_value - o.agreement_value)::numeric(15,2) AS amendment_value,
    c.agreement_value::numeric(15,2) AS current_value,
    ROUND(((c.agreement_value / NULLIF(o.agreement_value, 0)) - 1)::numeric, 6) AS amendment_ratio,
    COALESCE(c.agreement_type, 'Federal grant') AS solicitation_procedure,
    c.agreement_start_date::date AS contract_date,
    COALESCE(c.agreement_title_en, c.prog_name_en, 'Federal agreement') AS description,
    NULL::text AS procurement_id
  FROM fed.vw_agreement_current c
  INNER JOIN fed.vw_agreement_originals o
    ON c.ref_number = o.ref_number
   AND COALESCE(c.recipient_business_number, c.recipient_legal_name, c._id::text)
     = COALESCE(o.recipient_business_number, o.recipient_legal_name, o._id::text)
  WHERE o.agreement_value > %(min_original)s
    AND c.agreement_value > o.agreement_value
),
scored AS (SELECT * FROM paired)
"""


def _lane_fed_sql(conn, min_original: float, department: str, procedure: str, ranked_limit: int) -> dict[str, Any]:
  return _lane_generic_scored(conn, FED_SCORED_CTE, min_original, department, procedure, ranked_limit)


# ── AB lane ───────────────────────────────────────────────────────────────────

AB_SCORED_CTE = """
WITH matched AS (
  SELECT
    ss.contract_number AS reference_number,
    ss.vendor AS vendor_name,
    ss.ministry AS department,
    c.amount::numeric(15,2) AS original_value,
    ss.amount::numeric(15,2) AS amendment_value,
    (c.amount + ss.amount)::numeric(15,2) AS current_value,
    ROUND((ss.amount / NULLIF(c.amount, 0) - 1)::numeric, 6) AS amendment_ratio,
    'Non-competitive (sole source)' AS solicitation_procedure,
    COALESCE(ss.start_date::date, ss.display_fiscal_year::date) AS contract_date,
    CONCAT(ss.contract_services, ' | AB sole-source vs matched contract') AS description,
    NULL::text AS procurement_id
  FROM ab.ab_sole_source ss
  JOIN LATERAL (
    SELECT amount, display_fiscal_year
    FROM ab.ab_contracts c
    WHERE UPPER(TRIM(c.recipient)) = UPPER(TRIM(ss.vendor))
      AND c.ministry = ss.ministry
      AND c.amount IS NOT NULL
      AND c.amount >= %(min_original)s
    ORDER BY c.display_fiscal_year DESC NULLS LAST
    LIMIT 1
  ) c ON true
  WHERE ss.amount IS NOT NULL AND ss.amount > 0 AND ss.amount > c.amount
),
scored AS (SELECT * FROM matched)
"""


def _lane_ab_sql(conn, min_original: float, department: str, procedure: str, ranked_limit: int) -> dict[str, Any]:
    return _lane_generic_scored(conn, AB_SCORED_CTE, min_original, department, procedure, ranked_limit)


# ── CRA lane ──────────────────────────────────────────────────────────────────

CRA_SCORED_CTE = """
WITH scored AS (
  SELECT
    CONCAT(bn, ':', fiscal_year::text) AS reference_number,
    legal_name AS vendor_name,
    COALESCE(designation, 'CRA') AS department,
    GREATEST(revenue, 1)::numeric(15,2) AS original_value,
    total_govt::numeric(15,2) AS amendment_value,
    (COALESCE(revenue, 0) + COALESCE(total_govt, 0))::numeric(15,2) AS current_value,
    COALESCE(govt_share_of_rev, 0)::numeric(15,6) AS amendment_ratio,
    COALESCE(category, designation, 'Charity') AS solicitation_procedure,
    MAKE_DATE(fiscal_year, 12, 31) AS contract_date,
    CONCAT('CRA government funding share ', ROUND(COALESCE(govt_share_of_rev, 0) * 100, 1), '%') AS description,
    NULL::text AS procurement_id
  FROM cra.govt_funding_by_charity
  WHERE total_govt > %(min_original)s
    AND revenue IS NOT NULL
    AND revenue > 0
)
"""


def _lane_cra_sql(conn, min_original: float, department: str, procedure: str, ranked_limit: int) -> dict[str, Any]:
    data = _lane_generic_scored(
        conn,
        CRA_SCORED_CTE,
        min_original,
        department,
        procedure,
        ranked_limit,
        ratio_25=0.25,
        ratio_100=0.50,
        ratio_300=0.75,
        flagged_col="amendment_ratio > 0.25",
    )
    return data


# ── Entities lane ─────────────────────────────────────────────────────────────

ENTITIES_SCORED_CTE = """
WITH scored AS (
  SELECT
    entity_id::text AS reference_number,
    canonical_name AS vendor_name,
    COALESCE(array_to_string(dataset_sources, ', '), 'multi-source') AS department,
    GREATEST(
      COALESCE(cra_total_revenue, 0),
      COALESCE(fed_total_grants, 0),
      COALESCE(ab_total_contracts, 0),
      1
    )::numeric(15,2) AS original_value,
    (COALESCE(fed_total_grants, 0) + COALESCE(ab_total_grants, 0) + COALESCE(ab_total_sole_source, 0))::numeric(15,2)
      AS amendment_value,
    (
      COALESCE(fed_total_grants, 0) + COALESCE(ab_total_grants, 0)
      + COALESCE(ab_total_contracts, 0) + COALESCE(ab_total_sole_source, 0)
      + COALESCE(cra_total_revenue, 0)
    )::numeric(15,2) AS current_value,
    CASE
      WHEN COALESCE(cra_total_revenue, 0) > 0
      THEN (COALESCE(fed_total_grants, 0) / cra_total_revenue)::numeric(15,6)
      WHEN COALESCE(fed_total_grants, 0) > 0
      THEN 1.0
      ELSE 0.0
    END AS amendment_ratio,
    COALESCE(entity_type, 'entity') AS solicitation_procedure,
    CURRENT_DATE AS contract_date,
    CONCAT(source_count::text, ' linked sources | confidence ', ROUND(COALESCE(confidence, 0)::numeric, 2)) AS description,
    NULL::text AS procurement_id
  FROM general.vw_entity_funding
  WHERE source_count >= 2
    AND (
      COALESCE(fed_total_grants, 0) + COALESCE(ab_total_contracts, 0)
      + COALESCE(ab_total_sole_source, 0)
    ) > %(min_original)s
)
"""


def _lane_entities_sql(conn, min_original: float, department: str, procedure: str, ranked_limit: int) -> dict[str, Any]:
    return _lane_generic_scored(
        conn,
        ENTITIES_SCORED_CTE,
        min_original,
        department,
        procedure,
        ranked_limit,
        ratio_25=0.25,
        ratio_100=1.0,
        ratio_300=3.0,
        flagged_col="amendment_ratio > 0.25",
    )


def _lane_generic_scored(
    conn,
    scored_cte: str,
    min_original: float,
    department: str,
    procedure: str,
    ranked_limit: int,
    ratio_25: float = 0.25,
    ratio_100: float = 1.0,
    ratio_300: float = 3.0,
    flagged_col: str = "amendment_ratio > 0.25",
) -> dict[str, Any]:
    params: dict[str, Any] = {"min_original": float(min_original), "ranked_limit": int(ranked_limit)}

    kpis_sql = scored_cte + f"""
SELECT
  COUNT(*)::bigint AS contracts_scanned,
  COUNT(*) FILTER (WHERE amendment_ratio > {ratio_25})::bigint AS ratio_gt_25,
  COUNT(*) FILTER (WHERE amendment_ratio > {ratio_100})::bigint AS ratio_gt_100,
  COUNT(*) FILTER (WHERE amendment_ratio > {ratio_300})::bigint AS ratio_gt_300
FROM scored
WHERE 1=1
"""
    kpis_sql, fp = _apply_dept_proc_filters(kpis_sql, department, procedure)
    params.update(fp)
    kpis_row = _query_df(conn, kpis_sql, params).iloc[0].to_dict()

    dept_sql = scored_cte + f"""
SELECT
  department,
  COUNT(*)::bigint AS contracts,
  COUNT(*) FILTER (WHERE {flagged_col})::bigint AS flagged,
  AVG(amendment_ratio)::float AS avg_ratio,
  MAX(amendment_ratio)::float AS max_ratio
FROM scored
WHERE 1=1
"""
    dept_sql, fp = _apply_dept_proc_filters(dept_sql, "", procedure)
    params.update(fp)
    dept_sql += " GROUP BY department ORDER BY flagged DESC, avg_ratio DESC NULLS LAST LIMIT 10"
    dept_rollup = _query_df(conn, dept_sql, params)

    proc_sql = scored_cte + """
SELECT solicitation_procedure, COUNT(*)::bigint AS contracts
FROM scored
WHERE 1=1
"""
    proc_sql, fp = _apply_dept_proc_filters(proc_sql, department, "")
    params.update(fp)
    proc_sql += " GROUP BY solicitation_procedure ORDER BY contracts DESC LIMIT 10"
    proc_rollup = _query_df(conn, proc_sql, params)

    hist_sql = scored_cte + """
SELECT
  (FLOOR(LEAST(amendment_ratio * 100.0, 400.0) / 25.0) * 25.0)::float AS bin_start,
  COUNT(*)::bigint AS contracts
FROM scored
WHERE 1=1
"""
    hist_sql, fp = _apply_dept_proc_filters(hist_sql, department, procedure)
    params.update(fp)
    hist_sql += " GROUP BY 1 ORDER BY 1"
    hist_df = _query_df(conn, hist_sql, params)
    if not hist_df.empty:
        hist_df["bin_end"] = hist_df["bin_start"] + 25.0

    filters_sql = scored_cte + "SELECT DISTINCT department, solicitation_procedure FROM scored"
    filters_df = _query_df(conn, filters_sql, {"min_original": float(min_original)})

    ranked_sql = scored_cte + """
SELECT
  reference_number,
  vendor_name,
  department,
  original_value,
  amendment_value,
  current_value,
  (amendment_ratio * 100.0)::float AS ratio_pct,
  (amendment_ratio + 1.0)::float AS ratio_x,
  solicitation_procedure,
  procurement_id,
  contract_date,
  description
FROM scored
WHERE 1=1
"""
    ranked_sql, fp = _apply_dept_proc_filters(ranked_sql, department, procedure)
    params.update(fp)
    ranked_sql += " ORDER BY amendment_ratio DESC NULLS LAST LIMIT %(ranked_limit)s"
    ranked = _query_df(conn, ranked_sql, params)

    return {
        "kpis": {
            "contracts_scanned": int(kpis_row.get("contracts_scanned") or 0),
            "ratio_gt_25": int(kpis_row.get("ratio_gt_25") or 0),
            "ratio_gt_100": int(kpis_row.get("ratio_gt_100") or 0),
            "ratio_gt_300": int(kpis_row.get("ratio_gt_300") or 0),
        },
        "dept_rollup": dept_rollup,
        "proc_rollup": proc_rollup,
        "hist_df": hist_df,
        "ranked": ranked,
        "filter_departments": ["(all)"] + sorted(filters_df["department"].dropna().astype(str).unique().tolist()),
        "filter_procedures": ["(all)"] + sorted(filters_df["solicitation_procedure"].dropna().astype(str).unique().tolist()),
        "rows_in_lane": int(kpis_row.get("contracts_scanned") or 0),
    }


def fetch_lane_row(conn, lane: DatasetLane, reference_number: str, min_original: float) -> pd.Series | None:
    """Fetch one ranked row for governance drill-down."""
    if lane == "contracts":
        sql = CONTRACTS_SCORED_CTE + " SELECT * FROM scored WHERE reference_number = %(ref)s LIMIT 1"
    elif lane == "fed":
        sql = FED_SCORED_CTE + " SELECT * FROM scored WHERE reference_number = %(ref)s LIMIT 1"
    elif lane == "ab":
        sql = AB_SCORED_CTE + " SELECT * FROM scored WHERE reference_number = %(ref)s LIMIT 1"
    elif lane == "cra":
        sql = CRA_SCORED_CTE + " SELECT * FROM scored WHERE reference_number = %(ref)s LIMIT 1"
    elif lane == "entities":
        sql = ENTITIES_SCORED_CTE + " SELECT * FROM scored WHERE reference_number = %(ref)s LIMIT 1"
    else:
        return None
    df = _query_df(conn, sql, {"min_original": float(min_original), "ref": str(reference_number)})
    if df.empty:
        return None
    row = df.iloc[0].copy()
    if "solicitation_procedure_raw" not in row.index:
        row["solicitation_procedure_raw"] = row.get("solicitation_procedure", "")
    return row


def query_lane_aggregates(
    lane: DatasetLane,
    min_original: float,
    department: str,
    procedure: str,
    ranked_limit: int = RANKED_LIMIT,
) -> dict[str, Any]:
    if not db_config_present():
        raise RuntimeError("Database not configured")

    conn_str = _db_connection_string()
    with _pg_connect(conn_str) as conn:
        if not lane_available(conn, lane):
            return _empty_lane_payload(
                lane,
                f"Lane '{lane}' is not available on this database (missing table or view). "
                "Connect to the Agency 2026 unified Postgres warehouse.",
            )

        if lane == "contracts":
            return _lane_contracts_sql(conn, min_original, department, procedure, ranked_limit)
        if lane == "fed":
            return _lane_fed_sql(conn, min_original, department, procedure, ranked_limit)
        if lane == "ab":
            return _lane_ab_sql(conn, min_original, department, procedure, ranked_limit)
        if lane == "cra":
            return _lane_cra_sql(conn, min_original, department, procedure, ranked_limit)
        if lane == "entities":
            return _lane_entities_sql(conn, min_original, department, procedure, ranked_limit)

    return _empty_lane_payload(lane, f"Unknown lane: {lane}")
