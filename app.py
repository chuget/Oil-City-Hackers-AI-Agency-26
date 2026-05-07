"""
Streamlit UI for Public Contract Change Monitor.
Core logic lives in monitor_core.py / monitor_charts.py / monitor_dashboard.py.
HTML dashboard: uvicorn monitor_site.server:app (see README).
"""

from __future__ import annotations

import os

import altair as alt
import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from monitor_charts import (
    amendment_ratio_histogram_spec,
    dept_flagged_chart_spec,
    solicitation_procedure_chart_spec,
    timeline_chart_spec,
)
from monitor_core import (
    evaluate_gates,
    evidence_requirements_for,
    format_currency,
    format_ratio,
    load_contracts,
    load_real_timeline,
    synthesize_amendment_timeline,
    verdict_badge,
    claim_badge,
)
from monitor_dashboard import PC_RULE_REMINDERS


def _bridge_streamlit_secrets_to_environ() -> None:
    try:
        if not os.environ.get("DB_CONNECTION_STRING"):
            v = st.secrets.get("DB_CONNECTION_STRING", "")
            if str(v).strip():
                os.environ["DB_CONNECTION_STRING"] = str(v).strip()
        if not os.environ.get("DATABASE_URL"):
            v = st.secrets.get("DATABASE_URL", "")
            if str(v).strip():
                os.environ["DATABASE_URL"] = str(v).strip()
    except Exception:
        pass


def apply_ui_theme() -> None:
    st.markdown(
        """
        <style>
          :root {
            --bg-deep: #0B1220;
            --bg-panel: #0F172A;
            --bg-panel-soft: #111827;
            --line-soft: #1F2937;
            --line-strong: #334155;
            --text-main: #E5E7EB;
            --text-muted: #9CA3AF;
            --text-soft: #CBD5E1;
            --accent-blue: #38BDF8;
            --accent-green: #22C55E;
            --accent-amber: #F59E0B;
          }
          .block-container {max-width: 1320px; padding-top: 0.75rem; padding-bottom: 1.4rem;}
          h1, h2, h3 {letter-spacing: -0.015em;}
          .subtitle {color: var(--text-muted); margin-top: -0.25rem; margin-bottom: 0.7rem; font-size: 0.98rem;}
          .hero-card {
            background: linear-gradient(135deg, var(--bg-panel) 0%, var(--bg-panel-soft) 100%);
            border: 1px solid var(--line-soft);
            border-radius: 16px;
            padding: 15px 17px;
            margin: 0.18rem 0 0.45rem 0;
            box-shadow: 0 16px 40px rgba(2, 6, 23, 0.35);
          }
          .hero-title {font-size: 1.08rem; font-weight: 750; margin-bottom: 0.26rem; color: var(--text-main);}
          .hero-text {color: var(--text-soft); font-size: 0.95rem; line-height: 1.45;}
          .mission-strip {
            margin: 0.4rem 0 0.7rem 0;
            background: rgba(17, 24, 39, 0.82);
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            padding: 0.5rem 0.7rem;
            color: var(--text-soft);
            font-size: 0.86rem;
          }
          .section-shell {
            margin: 0.72rem 0 1rem 0;
            padding: 0.8rem 0.9rem 0.45rem 0.9rem;
            border-radius: 14px;
            border: 1px solid var(--line-soft);
            background: linear-gradient(180deg, rgba(15,23,42,0.70) 0%, rgba(15,23,42,0.52) 100%);
          }
          .section-title {
            font-weight: 720;
            font-size: 1.03rem;
            margin-bottom: 0.14rem;
            color: var(--text-main);
          }
          .section-note {
            color: var(--text-muted);
            font-size: 0.84rem;
            margin-bottom: 0.52rem;
          }
          .kpi-card {
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            background: linear-gradient(180deg, #0F172A 0%, #0D1525 100%);
            padding: 0.58rem 0.7rem;
            margin-bottom: 0.4rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
          }
          .kpi-label {
            color: var(--text-muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.035em;
            margin-bottom: 0.18rem;
          }
          .kpi-value {
            color: var(--text-main);
            font-size: 1.3rem;
            font-weight: 760;
            line-height: 1.05;
          }
          .info-chip {
            display:inline-block; padding:0.18rem 0.55rem; border-radius:999px;
            background:#1F2937; color:var(--text-soft); border:1px solid #374151;
            font-size:0.78rem; margin-right:0.35rem; margin-bottom:0.35rem;
          }
          .filter-hint {
            color: var(--text-muted);
            font-size: 0.81rem;
            margin: 0.15rem 0 0.35rem 0;
          }
          .status-chip {
            display:inline-block;
            padding: 0.14rem 0.5rem;
            border-radius: 999px;
            border: 1px solid var(--line-strong);
            background: rgba(2, 6, 23, 0.75);
            color: var(--text-soft);
            font-size: 0.75rem;
            margin-bottom: 0.35rem;
          }
          .gate-row {
            border: 1px solid var(--line-soft);
            border-radius: 10px;
            padding: 0.42rem 0.6rem;
            margin: 0.26rem 0;
            background: rgba(15, 23, 42, 0.65);
          }
          .panel-title {
            font-size: 0.88rem;
            font-weight: 670;
            margin-bottom: 0.28rem;
            color: var(--text-main);
          }
          [data-testid="stMetricValue"] {font-size: 1.7rem;}
          [data-testid="stMetricLabel"] {font-weight: 600;}
          [data-testid="stDataFrame"] {border-radius: 10px; border: 1px solid var(--line-soft);}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_section_shell(title: str, note: str) -> None:
    st.markdown(
        (
            "<div class='section-shell'>"
            f"<div class='section-title'>{title}</div>"
            f"<div class='section-note'>{note}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str) -> None:
    st.markdown(
        (
            "<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{value}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_filter_hint() -> None:
    st.markdown(
        "<div class='filter-hint'>Need filters? Open the left panel using the top-left arrow.</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Amendment Growth Tracker",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_ui_theme()
    _bridge_streamlit_secrets_to_environ()

    st.warning(
        "You are viewing the legacy Streamlit page. For the new HTML/CSS dashboard with graphs, "
        "run `python -m uvicorn monitor_site.server:app --reload --host 127.0.0.1 --port 8765` "
        "and open http://127.0.0.1:8765."
    )
    st.title("Public Contract Change Monitor")
    st.markdown(
        "<div class='subtitle'>A plain-language tool for spotting unusually large contract changes and explaining what can (and cannot) be claimed from open data.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='mission-strip'><b>Executive mission:</b> Surface high-growth amendment patterns quickly, then constrain interpretation through governance gates before any external claim.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class='hero-card'>
          <div class='hero-title'>What this site does</div>
          <div class='hero-text'>
            This app reviews public federal contract records and highlights cases where amendment value grew substantially beyond the original award.
            It does <b>not</b> decide wrongdoing. It classifies findings as:
            <b>FLAGGED</b> (pattern needs monitoring) or <b>INVESTIGATED</b> (stronger corroborated signal requiring follow-up evidence).
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<span class='info-chip'>Pattern detection only</span>"
        "<span class='info-chip'>No misconduct verdicts</span>"
        "<span class='info-chip'>Evidence-first governance gates</span>",
        unsafe_allow_html=True,
    )
    render_filter_hint()

    with st.expander("How to read this dashboard", expanded=False):
        st.write(
            "- **Contracts scanned:** total records matching your current filters.\n"
            "- **Ratio > 25% / 100% / 300%:** how large amendment growth is versus original value.\n"
            "- **Ranked list:** contracts sorted from largest growth pattern to smallest.\n"
            "- **Drill-down:** details for one selected contract and its timeline trend.\n"
            "- **Governance card:** bounded statement of what the evidence supports right now."
        )
        st.write(
            "Important: a high ratio is a **signal for review**, not proof of misconduct. "
            "Legitimate scope expansion can also produce large amendments."
        )

    with st.spinner("Loading contract data from database..."):
        df, load_src = load_contracts()

    load_source = "Database" if load_src == "database" else "CSV fallback"
    st.caption(f"Data source: {load_source} | Rows loaded: {len(df):,}")

    with st.sidebar:
        st.header("Filters")
        min_original = st.number_input("Min original value", min_value=0, value=10000, step=1000)
        departments = ["(all)"] + sorted(df["department"].dropna().unique().tolist())
        department = st.selectbox("Department", departments, index=0)
        procedures = ["(all)"] + sorted(df["solicitation_procedure"].dropna().unique().tolist())
        procedure = st.selectbox("Solicitation procedure", procedures, index=0)
        st.divider()
        st.subheader("Thresholds (dashboard)")
        t25 = st.checkbox("Show ratio > 25% (FLAGGED)", value=True, disabled=True)
        _ = (t25,)

    dff = df[df["original_value"] >= float(min_original)].copy()
    if department != "(all)":
        dff = dff[dff["department"] == department]
    if procedure != "(all)":
        dff = dff[dff["solicitation_procedure"] == procedure]

    overview_df = df[df["original_value"] >= float(min_original)].copy()
    if procedure != "(all)":
        overview_df = overview_df[overview_df["solicitation_procedure"] == procedure]

    render_section_shell(
        "1) Executive Snapshot",
        "Core signal coverage and threshold exposure for the currently scoped cohort.",
    )
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Contracts scanned", f"{len(dff):,}")
    with k2:
        render_kpi_card("Ratio > 25%", f"{(dff['amendment_ratio'] > 0.25).sum():,}")
    with k3:
        render_kpi_card("Ratio > 100%", f"{(dff['amendment_ratio'] > 1.0).sum():,}")
    with k4:
        render_kpi_card("Ratio > 300%", f"{(dff['amendment_ratio'] > 3.0).sum():,}")

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

    left, right = st.columns([1.05, 1])
    with left:
        st.markdown("**Top departments by amendment activity**")
        if department != "(all)":
            st.caption(
                "Department comparison stays broad for context; your department filter applies to ranked results and drill-down."
            )
        st.dataframe(
            dept_rollup,
            use_container_width=True,
            hide_index=True,
            column_config={
                "avg_ratio": st.column_config.NumberColumn(format="%.2f"),
                "max_ratio": st.column_config.NumberColumn(format="%.2f"),
            },
        )
    with right:
        with st.spinner("Rendering department chart..."):
            st.altair_chart(
                alt.Chart.from_dict(dept_flagged_chart_spec(dept_rollup)),
                use_container_width=True,
            )

    chart_left, chart_right = st.columns([1, 1])
    with chart_left:
        st.markdown("**Amendment ratio distribution**")
        with st.spinner("Rendering ratio distribution..."):
            st.altair_chart(
                alt.Chart.from_dict(amendment_ratio_histogram_spec(overview_df)),
                use_container_width=True,
            )
    with chart_right:
        st.markdown("**Solicitation procedure mix**")
        proc_rollup = (
            overview_df.groupby("solicitation_procedure", as_index=False)
            .agg(contracts=("reference_number", "count"))
            .sort_values("contracts", ascending=False)
            .head(10)
        )
        with st.spinner("Rendering solicitation mix..."):
            st.altair_chart(
                alt.Chart.from_dict(solicitation_procedure_chart_spec(proc_rollup)),
                use_container_width=True,
            )

    render_section_shell(
        "2) Ranked Contracts Workspace",
        "Contracts are ranked by amendment ratio from highest to lowest to prioritize immediate review.",
    )
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
        st.warning("No contracts match the current filter set. Adjust filters to continue.")
        return

    st.dataframe(
        ranked_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "original_value": st.column_config.NumberColumn(format="$%,.0f"),
            "amendment_value": st.column_config.NumberColumn(format="$%,.0f"),
            "current_value": st.column_config.NumberColumn(format="$%,.0f"),
            "ratio_pct": st.column_config.NumberColumn("amendment %", format="%.1f%%"),
            "ratio_x": st.column_config.NumberColumn("growth multiple", format="%.2fx"),
        },
    )

    default_ref = ranked_display["reference_number"].iloc[0] if len(ranked_display) else None
    selected_ref = st.selectbox(
        "Select a contract to drill down",
        options=ranked_display["reference_number"].tolist(),
        index=0 if default_ref else None,
    )
    contract = ranked[ranked["reference_number"] == selected_ref].iloc[0]

    render_section_shell(
        "3) Contract Investigation",
        "Focused review of one contract's profile, value progression, and timeline behavior.",
    )
    a, b = st.columns([1.2, 1])
    with a:
        st.markdown("<div class='panel-title'>Contract profile</div>", unsafe_allow_html=True)
        detail_rows = [
            ("Reference", contract["reference_number"]),
            ("Vendor", contract["vendor_name"]),
            ("Department", contract["department"]),
            ("Date", contract["contract_date"]),
            ("Solicitation procedure", contract["solicitation_procedure"]),
            ("Description", contract["description"]),
        ]
        for k, v in detail_rows:
            st.write(f"**{k}:** {v}")
    with b:
        st.markdown("<div class='panel-title'>Value trajectory summary</div>", unsafe_allow_html=True)
        st.write(f"**Original:** {format_currency(contract['original_value'])}")
        st.write(f"**Amendments:** {format_currency(contract['amendment_value'])}")
        st.write(f"**Current:** {format_currency(contract['current_value'])}")
        st.write(f"**Amendment ratio:** {format_ratio(contract['amendment_ratio'])}")

    timeline_df = pd.DataFrame()
    procurement_id = str(contract.get("procurement_id") or "").strip()
    if procurement_id:
        with st.spinner("Loading amendment timeline history..."):
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
            st.markdown(
                "<span class='status-chip'>Timeline source: Synthetic fallback</span>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<span class='status-chip'>Timeline source: Actual contract history</span>",
            unsafe_allow_html=True,
        )

    if not timeline_df.empty:
        tl_spec = timeline_chart_spec(timeline_df)
        if tl_spec:
            with st.spinner("Rendering amendment timeline..."):
                st.altair_chart(alt.Chart.from_dict(tl_spec), use_container_width=True)

    render_section_shell(
        "4) Governance Decision Console",
        "Gate-by-gate accountability checks that bound what can be said from the current evidence.",
    )
    gates, claim = evaluate_gates(contract, [])

    card_left, card_right = st.columns([1.2, 1])
    with card_left:
        st.markdown("<div class='panel-title'>Gate verdicts (AG-01 to AG-09)</div>", unsafe_allow_html=True)
        for g in gates:
            st.markdown(
                f"<div class='gate-row'><b>{g.gate}:</b> {verdict_badge(g.verdict)} - {g.rationale}</div>",
                unsafe_allow_html=True,
            )

    with card_right:
        st.markdown("<div class='panel-title'>Governed output</div>", unsafe_allow_html=True)
        st.markdown(
            f"**Claim validity:** {claim_badge(claim)}",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='panel-title'>Evidence requirements for escalation</div>", unsafe_allow_html=True)
        for item in evidence_requirements_for(claim):
            st.write(f"- {item}")
        st.markdown("<div class='panel-title'>PC rule reminders</div>", unsafe_allow_html=True)
        for rule in PC_RULE_REMINDERS:
            idx = rule.find(":")
            if idx > 0:
                st.write(f"- **{rule[:idx]}:**{rule[idx + 1 :]}")
            else:
                st.write(f"- {rule}")

    st.divider()
    st.caption(
        "Interpretation note: This tool supports triage and transparency analysis. "
        "Final determinations require official procurement files, amendment documentation, and external verification."
    )


if __name__ == "__main__":
    main()
