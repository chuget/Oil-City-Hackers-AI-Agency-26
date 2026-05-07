"""Assemble dashboard payload (tables, chart specs, governance) from monitor_core."""

from __future__ import annotations

from typing import Any

import pandas as pd

from monitor_charts import (
    amendment_ratio_histogram_spec,
    dept_flagged_chart_spec,
    solicitation_procedure_chart_spec,
    timeline_chart_spec,
)
from monitor_core import (
    db_config_present,
    evaluate_gates,
    evidence_requirements_for,
    format_currency,
    format_ratio,
    load_contracts,
    load_real_timeline,
    synthesize_amendment_timeline,
)


PC_RULE_REMINDERS = [
    "PC-01: Pattern is not verdict.",
    "PC-03: Claim strength must not exceed evidence strength.",
    "PC-05: Every threshold must be documented (25% anchored to PSPC CPN 2022-1).",
    "PC-10: Never use the word “fraud”.",
    "PC-12: Never use raw SUM of agreement_value (not applicable in dummy mode).",
]


def build_dashboard_payload(
    min_original: float,
    department: str,
    procedure: str,
    selected_ref: str | None,
) -> dict[str, Any]:
    df, load_source = load_contracts()

    if df.empty:
        return {
            "ok": False,
            "reason": "no_data",
            "message": (
                "Zero contract rows were returned. If using Postgres: set DB_CONNECTION_STRING or "
                "DATABASE_URL, adjust PGSSLMODE (try prefer for local), and verify the canonical SQL "
                "returns data. Without a DB URL, the app reads data/contracts.csv next to app.py."
            ),
            "load_source": load_source,
            "rows_loaded": 0,
            "database_config_present": False,
            "filter_departments": ["(all)"],
            "filter_procedures": ["(all)"],
            "kpis": {
                "contracts_scanned": 0,
                "ratio_gt_25": 0,
                "ratio_gt_100": 0,
                "ratio_gt_300": 0,
            },
            "chart_dept": None,
            "chart_hist": None,
            "chart_proc": None,
            "dept_rollup": [],
            "ranked": [],
            "hint": None,
        }

    filter_departments = ["(all)"] + sorted(df["department"].dropna().unique().tolist())
    filter_procedures = ["(all)"] + sorted(df["solicitation_procedure"].dropna().unique().tolist())

    dff = df[df["original_value"] >= float(min_original)].copy()
    if department != "(all)":
        dff = dff[dff["department"] == department]
    if procedure != "(all)":
        dff = dff[dff["solicitation_procedure"] == procedure]

    overview_df = df[df["original_value"] >= float(min_original)].copy()
    if procedure != "(all)":
        overview_df = overview_df[overview_df["solicitation_procedure"] == procedure]

    kpis = {
        "contracts_scanned": int(len(dff)),
        "ratio_gt_25": int((dff["amendment_ratio"] > 0.25).sum()),
        "ratio_gt_100": int((dff["amendment_ratio"] > 1.0).sum()),
        "ratio_gt_300": int((dff["amendment_ratio"] > 3.0).sum()),
    }

    dept_rollup = (
        overview_df.assign(flagged=overview_df["amendment_ratio"] > 0.25)
        .groupby("department", as_index=False)
        .agg(
            contracts=("reference_number", "count"),
            flagged=("flagged", "sum"),
            avg_ratio=("amendment_ratio", "mean"),
            max_ratio=("amendment_ratio", "max"),
        )
        .sort_values(["flagged", "avg_ratio"], ascending=False)
        .head(10)
    )

    proc_rollup = (
        overview_df.groupby("solicitation_procedure", as_index=False)
        .agg(contracts=("reference_number", "count"))
        .sort_values("contracts", ascending=False)
        .head(10)
    )

    chart_dept = dept_flagged_chart_spec(dept_rollup)
    chart_hist = amendment_ratio_histogram_spec(overview_df)
    chart_proc = solicitation_procedure_chart_spec(proc_rollup)

    ranked = dff.sort_values("amendment_ratio", ascending=False).copy()
    ranked["ratio_pct"] = ranked["amendment_ratio"] * 100
    ranked["ratio_x"] = ranked["amendment_ratio"] + 1
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

    if ranked_display.empty:
        hint = None
        if len(df) > 0:
            hint = (
                "The database returned rows, but none match your current filters. "
                "Lower **Min original value** or set **Department** and **Solicitation procedure** to (all)."
            )
        return {
            "ok": False,
            "reason": "no_contracts",
            "hint": hint,
            "load_source": load_source,
            "rows_loaded": int(len(df)),
            "database_config_present": db_config_present(),
            "filter_departments": filter_departments,
            "filter_procedures": filter_procedures,
            "kpis": kpis,
            "chart_dept": chart_dept,
            "chart_hist": chart_hist,
            "chart_proc": chart_proc,
            "dept_rollup": dept_rollup.to_dict(orient="records"),
            "ranked": [],
        }

    refs = ranked_display["reference_number"].astype(str).tolist()
    if selected_ref and str(selected_ref) in refs:
        use_ref = str(selected_ref)
    else:
        use_ref = str(ranked_display["reference_number"].iloc[0])

    contract = ranked[ranked["reference_number"].astype(str) == use_ref].iloc[0]

    timeline_df = pd.DataFrame()
    procurement_id = str(contract.get("procurement_id") or "").strip()
    timeline_source = "none"
    if procurement_id:
        timeline_df = load_real_timeline(procurement_id)

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
            timeline_df["amendment_added"] = pd.to_numeric(
                timeline_df.get("amendment_added"), errors="coerce"
            )
            timeline_df["running_total"] = pd.to_numeric(
                timeline_df.get("running_total"), errors="coerce"
            )
            timeline_source = "synthetic"
    else:
        timeline_source = "actual"

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
        "original": format_currency(float(contract["original_value"]) if pd.notna(contract["original_value"]) else None),
        "amendments": format_currency(float(contract["amendment_value"]) if pd.notna(contract["amendment_value"]) else None),
        "current": format_currency(float(contract["current_value"]) if pd.notna(contract["current_value"]) else None),
        "amendment_ratio": format_ratio(float(contract["amendment_ratio"]) if pd.notna(contract["amendment_ratio"]) else None),
    }

    return {
        "ok": True,
        "hint": None,
        "load_source": load_source,
        "rows_loaded": int(len(df)),
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
