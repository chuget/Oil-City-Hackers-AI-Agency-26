from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import os
from pathlib import Path
from typing import Literal

import altair as alt
import pandas as pd
import psycopg
import streamlit as st


DATA_PATH = Path(__file__).parent / "data" / "contracts.csv"
SQL_PATH = Path(__file__).parent / "dev1-sql" / "DEV1_CANONICAL_SQL_CONTRACT.sql"


GateVerdict = Literal["PASS", "PARTIAL", "FAIL", "HOLD", "PROVISIONAL", "CONFIRMED"]
ClaimValidity = Literal["FLAGGED", "INVESTIGATED", "CLEARED", "CRITICAL"]


@dataclass(frozen=True)
class GateResult:
    gate: str
    verdict: GateVerdict
    rationale: str


def _badge(text: str, bg: str, fg: str = "#0b1220") -> str:
    safe = str(text).replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<span style='display:inline-block;"
        f"padding:0.14rem 0.6rem;border-radius:999px;"
        f"background:{bg};color:{fg};font-weight:800;"
        f"font-size:0.80rem;letter-spacing:0.03em;"
        f"border:1px solid rgba(255,255,255,0.18);"
        f"box-shadow:0 0 0 1px rgba(0,0,0,0.35), 0 6px 18px rgba(0,0,0,0.25)'>"
        f"{safe}"
        f"</span>"
    )


def verdict_badge(verdict: GateVerdict) -> str:
    v = str(verdict).upper()
    if v == "PASS":
        return _badge(v, bg="#22C55E", fg="#062B12")  # green (strong)
    if v == "PARTIAL":
        return _badge(v, bg="#F59E0B", fg="#2A1700")  # amber (strong)
    if v == "FAIL":
        return _badge(v, bg="#EF4444", fg="#2A0606")  # red (strong)
    if v == "HOLD":
        return _badge(v, bg="#F97316", fg="#2A1203")  # orange (strong)
    if v == "PROVISIONAL":
        return _badge(v, bg="#38BDF8", fg="#03202D")  # sky (strong)
    if v == "CONFIRMED":
        return _badge(v, bg="#3B82F6", fg="#04142E")  # blue (strong)
    return _badge(v, bg="#E5E7EB", fg="#111827")  # gray fallback


def claim_badge(claim: ClaimValidity) -> str:
    c = str(claim).upper()
    if c == "CLEARED":
        return _badge(c, bg="#22C55E", fg="#062B12")
    if c == "FLAGGED":
        return _badge(c, bg="#F59E0B", fg="#2A1700")
    if c == "INVESTIGATED":
        return _badge(c, bg="#F97316", fg="#2A1203")
    if c == "CRITICAL":
        return _badge(c, bg="#EF4444", fg="#2A0606")
    return _badge(c, bg="#E5E7EB", fg="#111827")


def _safe_ratio(amendment_value: float, original_value: float) -> float | None:
    if original_value is None or original_value == 0:
        return None
    if amendment_value is None:
        return None
    return (float(amendment_value) / float(original_value)) - 1.0


def _is_non_competitive(contract: pd.Series) -> bool:
    raw = str(contract.get("solicitation_procedure_raw") or "").strip().upper()
    label = str(contract.get("solicitation_procedure") or "").strip().lower()
    return raw in {"TN", "AC"} or "non-competitive" in label


@st.cache_data(show_spinner=False)
def load_contracts() -> pd.DataFrame:
    conn_str = os.environ.get("DB_CONNECTION_STRING", "").strip()
    if conn_str:
        sql = SQL_PATH.read_text(encoding="utf-8").split(";")[0].strip()
        with psycopg.connect(conn_str, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=cols)
        df["contract_or_agreement_date"] = pd.to_datetime(
            df["contract_or_agreement_date"], errors="coerce"
        ).dt.date
        df = df.rename(
            columns={
                "contract_or_agreement_date": "contract_date",
                "vendor": "vendor_name",
            }
        )
        if "reference_number" not in df.columns:
            # Canonical SQL output does not currently include reference_number.
            # Use record_id as a stable surrogate for UI grouping/selection.
            df["reference_number"] = df["record_id"]
        if "description" not in df.columns:
            df["description"] = "Not provided in canonical output."
        return df

    st.warning("DB_CONNECTION_STRING not set; using local CSV fallback data.")
    df = pd.read_csv(DATA_PATH)
    df["contract_date"] = pd.to_datetime(df["contract_date"], errors="coerce").dt.date
    for col in ["original_value", "amendment_value", "current_value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["amendment_ratio"] = [
        _safe_ratio(a, o) for a, o in zip(df["amendment_value"], df["original_value"])
    ]
    df = df.dropna(subset=["amendment_ratio", "original_value", "amendment_value"])
    if "solicitation_procedure_raw" not in df.columns:
        df["solicitation_procedure_raw"] = df["solicitation_procedure"]
    return df


def format_currency(x: float | None) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"${x:,.0f}"


def format_ratio(r: float | None) -> str:
    if r is None or pd.isna(r):
        return "—"
    return f"{r * 100:.1f}%"


def classify_claim(contract: pd.Series) -> ClaimValidity:
    ratio = float(contract["amendment_ratio"])
    sole_source = _is_non_competitive(contract)

    # Detection-first: we keep claim strength conservative and non-accusatory.
    if ratio > 3.0 and sole_source:
        return "CRITICAL"
    if ratio > 1.0 and sole_source:
        return "INVESTIGATED"
    if ratio > 0.25:
        return "FLAGGED"
    return "CLEARED"


def synthesize_amendment_timeline(contract: pd.Series) -> list[dict]:
    """
    Dummy timeline for demo purposes.
    - Competitive: 1 amendment step
    - Non-competitive: 3 steps
    """
    d = contract.get("contract_date")
    if isinstance(d, datetime):
        d = d.date()
    if not isinstance(d, date):
        d = date(2024, 1, 1)

    original = float(contract["original_value"])
    amendment = float(contract["amendment_value"])
    current = float(contract["current_value"])
    if _is_non_competitive(contract):
        steps = [0.35, 0.70, 1.00]
        labels = ["Amendment A", "Amendment B", "Amendment C"]
    else:
        steps = [1.00]
        labels = ["Amendment"]

    timeline = []
    for i, (p, label) in enumerate(zip(steps, labels)):
        timeline.append(
            {
                "date": d + timedelta(days=30 * (i + 1)),
                "label": label,
                "amendment_added": amendment * p,
                "running_total": original + amendment * p,
            }
        )

    # Ensure last point matches the current_value if present; otherwise, original+amendment.
    if timeline:
        timeline[-1]["running_total"] = current if current else (original + amendment)
    return timeline


def evaluate_gates(contract: pd.Series, timeline: list[dict]) -> tuple[list[GateResult], ClaimValidity]:
    required_fields = [
        ("reference_number", "reference number"),
        ("vendor_name", "vendor name"),
        ("department", "department"),
        ("original_value", "original value"),
        ("amendment_value", "amendment value"),
    ]
    missing = [label for key, label in required_fields if not contract.get(key) or pd.isna(contract.get(key))]
    ag01: GateResult
    if missing:
        ag01 = GateResult(
            "AG-01 Evidence Provenance",
            "FAIL",
            "Missing required fields: " + ", ".join(missing) + ".",
        )
    else:
        ag01 = GateResult(
            "AG-01 Evidence Provenance",
            "PASS",
            "Traceable fields present (reference, vendor, department, values).",
        )

    vendor = str(contract.get("vendor_name") or "").strip()
    if not vendor:
        ag02 = GateResult("AG-02 Identity Resolution", "FAIL", "Vendor identifier missing.")
    else:
        ag02 = GateResult(
            "AG-02 Identity Resolution",
            "PARTIAL",
            "Vendor name present; no BN/golden record in dummy dataset.",
        )

    ratio = float(contract["amendment_ratio"])
    sole_source = _is_non_competitive(contract)
    claim = classify_claim(contract)

    if ratio > 1.0 and sole_source:
        ag03 = GateResult(
            "AG-03 Claim Strength",
            "PASS",
            "Ratio > 100% and non-competitive: defensible escalation to INVESTIGATED (still non-accusatory).",
        )
    elif ratio > 0.25:
        ag03 = GateResult(
            "AG-03 Claim Strength",
            "PASS",
            "Ratio > 25%: pattern detected → FLAGGED (not a verdict).",
        )
    else:
        ag03 = GateResult(
            "AG-03 Claim Strength",
            "PASS",
            "Below 25% threshold: likely CLEARED for this detector.",
        )

    if claim == "CRITICAL":
        ag04 = GateResult(
            "AG-04 Harm Boundary",
            "HOLD",
            "CRITICAL class is prohibited without external audit confirmation; hold escalation.",
        )
    else:
        ag04 = GateResult(
            "AG-04 Harm Boundary",
            "PASS",
            "Output remains pattern-based and non-accusatory; safe to display as governed finding.",
        )

    if len(timeline) <= 1:
        ag05 = GateResult(
            "AG-05 Temporal Window",
            "PROVISIONAL",
            "Single amendment step in dummy timeline: treat as provisional.",
        )
    else:
        ag05 = GateResult(
            "AG-05 Temporal Window",
            "CONFIRMED",
            "Multiple amendment steps in dummy timeline: pattern persists across periods.",
        )

    if not _is_non_competitive(contract):
        ag06 = GateResult(
            "AG-06 Program/Policy Coherence",
            "PASS",
            "Competitive procurement suggests original competition existed; creep may be anomalous (explanation not ruled out).",
        )
    else:
        ag06 = GateResult(
            "AG-06 Program/Policy Coherence",
            "PASS",
            "Non-competitive indicates sole-source context; amendment compounding risk is higher.",
        )

    gates = [ag01, ag02, ag03, ag04, ag05, ag06]

    # Sequential gating: if upstream fails, downstream claims must not escalate.
    if ag01.verdict == "FAIL":
        claim = "FLAGGED"
    return gates, claim


def evidence_requirements_for(claim: ClaimValidity) -> list[str]:
    if claim == "INVESTIGATED":
        return [
            "Procurement file / statement of work for original contract",
            "Amendment documentation (scope changes + approvals)",
            "Independent verification of vendor identity (BN / registry record)",
            "Third-party context to rule out legitimate scope expansion",
        ]
    if claim == "CRITICAL":
        return [
            "External audit confirmation (required before consequential escalation)",
            "Complete procurement file chain (original + all amendments)",
            "Independent corroboration from official sources",
        ]
    if claim == "FLAGGED":
        return [
            "Basic contract record completeness check",
            "Confirm thresholding logic and definitions used",
        ]
    return ["No additional evidence required (detector indicates low risk)."]


def main() -> None:
    st.set_page_config(page_title="Amendment Growth Tracker", layout="wide")

    st.title("Amendment Growth Tracker")
    st.caption("Detection surfaces patterns. Governance determines what we are permitted to say about them.")

    df = load_contracts()

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
        _ = (t25,)  # keep UI anchored to spec

    dff = df[df["original_value"] >= float(min_original)].copy()
    if department != "(all)":
        dff = dff[dff["department"] == department]
    if procedure != "(all)":
        dff = dff[dff["solicitation_procedure"] == procedure]

    # --- View 1: Dashboard ---
    st.subheader("View 1 — Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Contracts scanned", f"{len(dff):,}")
    c2.metric("Ratio > 25%", f"{(dff['amendment_ratio'] > 0.25).sum():,}")
    c3.metric("Ratio > 100%", f"{(dff['amendment_ratio'] > 1.0).sum():,}")
    c4.metric("Ratio > 300%", f"{(dff['amendment_ratio'] > 3.0).sum():,}")

    dept_rollup = (
        dff.assign(flagged=dff["amendment_ratio"] > 0.25)
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

    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Top departments by amendment activity**")
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
        chart = (
            alt.Chart(dept_rollup)
            .mark_bar()
            .encode(
                x=alt.X("flagged:Q", title="Flagged count (ratio > 25%)"),
                y=alt.Y("department:N", sort="-x", title=None),
                tooltip=["department", "contracts", "flagged", alt.Tooltip("avg_ratio:Q", format=".2f")],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, use_container_width=True)

    # --- View 2: Ranked Contract List ---
    st.subheader("View 2 — Ranked Contract List")
    ranked = dff.sort_values("amendment_ratio", ascending=False).copy()
    ranked_display = ranked[
        [
            "reference_number",
            "vendor_name",
            "department",
            "original_value",
            "amendment_value",
            "current_value",
            "amendment_ratio",
            "solicitation_procedure",
        ]
    ].copy()

    st.dataframe(
        ranked_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "original_value": st.column_config.NumberColumn(format="$%,.0f"),
            "amendment_value": st.column_config.NumberColumn(format="$%,.0f"),
            "current_value": st.column_config.NumberColumn(format="$%,.0f"),
            "amendment_ratio": st.column_config.NumberColumn(format="%.3f"),
        },
    )

    default_ref = ranked_display["reference_number"].iloc[0] if len(ranked_display) else None
    selected_ref = st.selectbox(
        "Select a contract to drill down",
        options=ranked_display["reference_number"].tolist(),
        index=0 if default_ref else None,
    )
    contract = ranked[ranked["reference_number"] == selected_ref].iloc[0]

    # --- View 3: Contract Drill-Down ---
    st.subheader("View 3 — Contract Drill-Down")
    a, b = st.columns([1.2, 1])
    with a:
        st.markdown("**Contract details**")
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
        st.markdown("**Value summary**")
        st.write(f"**Original:** {format_currency(contract['original_value'])}")
        st.write(f"**Amendments:** {format_currency(contract['amendment_value'])}")
        st.write(f"**Current:** {format_currency(contract['current_value'])}")
        st.write(f"**Amendment ratio:** {format_ratio(contract['amendment_ratio'])}")

    timeline = synthesize_amendment_timeline(contract)
    if timeline:
        tl_df = pd.DataFrame(timeline)
        tl_df["date"] = pd.to_datetime(tl_df["date"])
        st.markdown("**Amendment timeline (synthetic demo)**")
        tl_chart = (
            alt.Chart(tl_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("running_total:Q", title="Running contract value", axis=alt.Axis(format="$,.0f")),
                tooltip=["label", alt.Tooltip("running_total:Q", format="$,.0f")],
            )
            .properties(height=220)
        )
        st.altair_chart(tl_chart, use_container_width=True)

    # --- View 4: Governance Finding Card ---
    st.subheader("View 4 — Governance Finding Card")
    gates, claim = evaluate_gates(contract, timeline)

    card_left, card_right = st.columns([1.2, 1])
    with card_left:
        st.markdown("**Gate verdicts (AG-01 → AG-06)**")
        for g in gates:
            st.markdown(
                f"**{g.gate}:** {verdict_badge(g.verdict)} — {g.rationale}",
                unsafe_allow_html=True,
            )

    with card_right:
        st.markdown("**Governed output**")
        st.markdown(
            f"**Claim validity:** {claim_badge(claim)}",
            unsafe_allow_html=True,
        )
        st.markdown("**Evidence requirements for escalation**")
        for item in evidence_requirements_for(claim):
            st.write(f"- {item}")
        st.markdown("**PC rule reminders**")
        st.write("- **PC-01:** Pattern is not verdict.")
        st.write("- **PC-03:** Claim strength must not exceed evidence strength.")
        st.write("- **PC-05:** Every threshold must be documented (25% anchored to PSPC CPN 2022-1).")
        st.write("- **PC-10:** Never use the word “fraud”.")
        st.write("- **PC-12:** Never use raw SUM of agreement_value (not applicable in dummy mode).")


if __name__ == "__main__":
    main()

