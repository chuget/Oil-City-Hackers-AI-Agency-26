"""Assemble dashboard payload (tables, chart specs, governance) via SQL lanes."""

from __future__ import annotations

from typing import Any

import pandas as pd

from monitor_charts import (
    dept_flagged_chart_spec,
    histogram_bins_chart_spec,
    solicitation_procedure_chart_spec,
    timeline_chart_spec,
)
from monitor_core import (
    db_config_present,
    evaluate_gates,
    evidence_requirements_for,
    format_currency,
    format_ratio,
    load_real_timeline,
    synthesize_amendment_timeline,
)
from monitor_data_platform import (
    LANE_META,
    RANKED_LIMIT,
    DatasetLane,
    fetch_lane_row,
    query_lane_aggregates,
)


PC_RULE_REMINDERS = [
    "PC-01: Pattern is not verdict.",
    "PC-03: Claim strength must not exceed evidence strength.",
    "PC-05: Every threshold must be documented (25% anchored to PSPC CPN 2022-1 on the contracts lane).",
    "PC-10: Never use the word “fraud”.",
    "PC-12: Never use raw SUM of agreement_value on federal grants (use vw_agreement_current).",
]


def _hist_x_title(dataset: str) -> str:
    if dataset == "cra":
        return "Government share of revenue (%)"
    return "Amendment ratio (%)"


def build_dashboard_payload(
    min_original: float,
    department: str,
    procedure: str,
    selected_ref: str | None,
    dataset: str = "contracts",
) -> dict[str, Any]:
    lane: DatasetLane = dataset if dataset in LANE_META else "contracts"  # type: ignore[assignment]
    lane_label = LANE_META.get(lane, {}).get("label", lane)

    if not db_config_present():
        return {
            "ok": False,
            "reason": "no_db",
            "message": (
                "Set DB_CONNECTION_STRING or DATABASE_URL to the Agency 2026 unified Postgres warehouse. "
                "Without it, only the small data/contracts.csv sample is available via the legacy path."
            ),
            "dataset": lane,
            "dataset_label": lane_label,
            "load_source": "none",
            "rows_loaded": 0,
            "rows_in_lane": 0,
            "rows_returned_ranked": 0,
            "database_config_present": False,
            "filter_departments": ["(all)"],
            "filter_procedures": ["(all)"],
            "kpis": {"contracts_scanned": 0, "ratio_gt_25": 0, "ratio_gt_100": 0, "ratio_gt_300": 0},
            "chart_dept": None,
            "chart_hist": None,
            "chart_proc": None,
            "dept_rollup": [],
            "ranked": [],
            "hint": None,
        }

    try:
        agg = query_lane_aggregates(lane, min_original, department, procedure, RANKED_LIMIT)
    except Exception as e:
        return {
            "ok": False,
            "reason": "server_error",
            "message": str(e),
            "dataset": lane,
            "dataset_label": lane_label,
            "load_source": "database",
            "rows_loaded": 0,
            "rows_in_lane": 0,
            "rows_returned_ranked": 0,
            "database_config_present": db_config_present(),
            "filter_departments": ["(all)"],
            "filter_procedures": ["(all)"],
            "kpis": {"contracts_scanned": 0, "ratio_gt_25": 0, "ratio_gt_100": 0, "ratio_gt_300": 0},
            "dept_rollup": [],
            "ranked": [],
            "hint": None,
        }

    if agg.get("reason") == "lane_unavailable":
        return {
            **agg,
            "dataset": lane,
            "dataset_label": lane_label,
            "load_source": "database",
            "database_config_present": db_config_present(),
            "chart_dept": None,
            "chart_hist": None,
            "chart_proc": None,
            "hint": agg.get("message"),
        }

    kpis = agg["kpis"]
    dept_rollup = agg["dept_rollup"]
    proc_rollup = agg["proc_rollup"]
    hist_df = agg.get("hist_df", pd.DataFrame())
    ranked = agg["ranked"]
    rows_in_lane = int(agg.get("rows_in_lane", 0))
    rows_returned = int(len(ranked))

    chart_dept = dept_flagged_chart_spec(dept_rollup)
    chart_hist = histogram_bins_chart_spec(hist_df, x_title=_hist_x_title(lane))
    chart_proc = solicitation_procedure_chart_spec(proc_rollup)

    filter_departments = agg.get("filter_departments", ["(all)"])
    filter_procedures = agg.get("filter_procedures", ["(all)"])

    if ranked.empty:
        hint = (
            "No records match your current filters in this data lane. "
            "Lower **Min original value** or reset **Department** and **Procedure** to (all)."
        )
        return {
            "ok": False,
            "reason": "no_contracts",
            "hint": hint,
            "dataset": lane,
            "dataset_label": lane_label,
            "load_source": "database",
            "rows_loaded": rows_in_lane,
            "rows_in_lane": rows_in_lane,
            "rows_returned_ranked": 0,
            "ranked_limit": RANKED_LIMIT,
            "database_config_present": db_config_present(),
            "filter_departments": filter_departments,
            "filter_procedures": filter_procedures,
            "department_note": department != "(all)",
            "kpis": kpis,
            "chart_dept": chart_dept,
            "chart_hist": chart_hist,
            "chart_proc": chart_proc,
            "dept_rollup": dept_rollup.to_dict(orient="records") if hasattr(dept_rollup, "to_dict") else [],
            "ranked": [],
        }

    ranked_display = ranked[
        [
            "reference_number",
            "vendor_name",
            "department",
            "original_value",
            "amendment_value",
            "current_value",
            "ratio_pct",
            "ratio_x",
            "solicitation_procedure",
        ]
    ].copy()

    refs = ranked_display["reference_number"].astype(str).tolist()
    use_ref = str(selected_ref) if selected_ref and str(selected_ref) in refs else str(ranked_display["reference_number"].iloc[0])

    from monitor_core import _db_connection_string, _pg_connect

    contract = None
    with _pg_connect(_db_connection_string()) as conn:
        contract = fetch_lane_row(conn, lane, use_ref, min_original)

    if contract is None:
        contract = ranked[ranked["reference_number"].astype(str) == use_ref].iloc[0]

    timeline_df = pd.DataFrame()
    timeline_source = "none"
    procurement_id = str(contract.get("procurement_id") or "").strip()
    if lane == "contracts" and procurement_id:
        timeline_df = load_real_timeline(procurement_id)
        if not timeline_df.empty:
            timeline_source = "actual"

    if timeline_df.empty:
        timeline = synthesize_amendment_timeline(contract)
        if timeline:
            timeline_df = pd.DataFrame(timeline)
            timeline_df["date"] = pd.to_datetime(timeline_df["date"])
            timeline_df["label"] = timeline_df["label"].fillna("Synthetic point")
            timeline_df = timeline_df.reset_index(drop=True)
            timeline_df["timeline_step"] = timeline_df.index + 1
            timeline_df["effective_date"] = timeline_df["date"]
            timeline_df["time_detail"] = (
                "Step "
                + timeline_df["timeline_step"].astype(str)
                + " | "
                + timeline_df["date"].dt.strftime("%Y-%m-%d").fillna("unknown-date")
            )
            timeline_df["amendment_added"] = pd.to_numeric(timeline_df.get("amendment_added"), errors="coerce")
            timeline_df["running_total"] = pd.to_numeric(timeline_df.get("running_total"), errors="coerce")
            timeline_source = "synthetic"

    if not timeline_df.empty:
        timeline_df = timeline_df.copy()
        timeline_df["effective_date"] = pd.to_datetime(timeline_df["effective_date"], errors="coerce")
        timeline_df = timeline_df.sort_values(
            ["effective_date", "timeline_step"] if "timeline_step" in timeline_df.columns else ["effective_date"],
            na_position="last",
        ).reset_index(drop=True)
    chart_timeline = timeline_chart_spec(timeline_df) if not timeline_df.empty else None

    gates, claim = evaluate_gates(contract, [])
    gates_out = [{"gate": g.gate, "verdict": g.verdict, "rationale": g.rationale} for g in gates]

    profile = {
        "reference_number": contract.get("reference_number"),
        "vendor_name": contract.get("vendor_name"),
        "department": contract.get("department"),
        "contract_date": str(contract.get("contract_date") or ""),
        "solicitation_procedure": contract.get("solicitation_procedure"),
        "description": contract.get("description"),
    }
    value_summary = {
        "original": format_currency(float(contract["original_value"]) if pd.notna(contract.get("original_value")) else None),
        "amendments": format_currency(float(contract["amendment_value"]) if pd.notna(contract.get("amendment_value")) else None),
        "current": format_currency(float(contract["current_value"]) if pd.notna(contract.get("current_value")) else None),
        "amendment_ratio": format_ratio(float(contract["amendment_ratio"]) if pd.notna(contract.get("amendment_ratio")) else None),
    }

    ranked_note = None
    if rows_in_lane > rows_returned:
        ranked_note = (
            f"Showing top {rows_returned:,} of {rows_in_lane:,} in-scope records "
            f"(SQL limit; full warehouse has millions of rows in other lanes)."
        )

    return {
        "ok": True,
        "hint": None,
        "dataset": lane,
        "dataset_label": lane_label,
        "load_source": "database",
        "rows_loaded": rows_in_lane,
        "rows_in_lane": rows_in_lane,
        "rows_returned_ranked": rows_returned,
        "ranked_limit": RANKED_LIMIT,
        "ranked_note": ranked_note,
        "database_config_present": db_config_present(),
        "filter_departments": filter_departments,
        "filter_procedures": filter_procedures,
        "department_note": department != "(all)",
        "kpis": kpis,
        "dept_rollup": dept_rollup.to_dict(orient="records"),
        "chart_dept": chart_dept,
        "chart_hist": chart_hist,
        "chart_proc": chart_proc,
        "ranked": ranked_display.to_dict(orient="records"),
        "selected_ref": use_ref,
        "profile": profile,
        "value_summary": value_summary,
        "timeline_source": timeline_source,
        "chart_timeline": chart_timeline,
        "gates": gates_out,
        "claim": claim,
        "evidence": evidence_requirements_for(claim),
        "pc_rules": PC_RULE_REMINDERS,
    }
