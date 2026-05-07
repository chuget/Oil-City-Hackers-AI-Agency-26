"""Altair charts as Vega-Lite specs for the contract monitor."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd


def _empty_chart_spec(message: str, height: int = 220) -> dict[str, Any]:
    ch = (
        alt.Chart(pd.DataFrame({"t": [message]}))
        .mark_text(fontSize=13, color="#64748B", align="left", lineHeight=18)
        .encode(text="t:N", x=alt.value(8), y=alt.value(10))
        .properties(height=height, width=420)
    )
    spec = executive_chart_style(ch, height).to_dict()
    spec["background"] = "transparent"
    return spec


def executive_chart_style(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height, background="transparent")
        .configure_axis(
            labelColor="#475569",
            titleColor="#475569",
            gridColor="#E2E8F0",
            tickColor="#CBD5E1",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_view(stroke="transparent")
        .configure_title(color="#0F172A", fontSize=13)
        .configure_legend(
            labelColor="#475569",
            titleColor="#0F172A",
        )
    )


def dept_flagged_chart_spec(dept_rollup: pd.DataFrame) -> dict[str, Any]:
    if dept_rollup.empty:
        return _empty_chart_spec("No department data to chart (dataset may be empty or fully filtered).")
    chart = executive_chart_style(
        alt.Chart(dept_rollup)
        .mark_bar()
        .encode(
            x=alt.X("flagged:Q", title="Flagged count (ratio > 25%)"),
            y=alt.Y("department:N", sort="-x", title=None),
            tooltip=["department", "contracts", "flagged", alt.Tooltip("avg_ratio:Q", format=".2f")],
        ),
        height=280,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec


def amendment_ratio_histogram_spec(overview_df: pd.DataFrame) -> dict[str, Any]:
    if overview_df.empty or "amendment_ratio" not in overview_df.columns:
        return _empty_chart_spec("No contracts in scope for ratio distribution.", height=200)

    ratios = pd.to_numeric(overview_df["amendment_ratio"], errors="coerce").dropna() * 100
    if ratios.empty:
        return _empty_chart_spec("No numeric amendment ratios in scope.", height=200)

    bin_count = min(30, max(1, int(ratios.nunique())))
    if bin_count == 1:
        center = float(ratios.iloc[0])
        hist_df = pd.DataFrame(
            {
                "bin_start": [center - 0.5],
                "bin_end": [center + 0.5],
                "contracts": [int(len(ratios))],
            }
        )
    else:
        bins = pd.cut(ratios, bins=bin_count, include_lowest=True)
        hist_df = (
            bins.value_counts(sort=False)
            .rename_axis("bin")
            .reset_index(name="contracts")
        )
        hist_df["bin_start"] = hist_df["bin"].map(lambda x: float(x.left))
        hist_df["bin_end"] = hist_df["bin"].map(lambda x: float(x.right))
        hist_df = hist_df[["bin_start", "bin_end", "contracts"]]

    chart = executive_chart_style(
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X("bin_start:Q", title="Amendment ratio (%)"),
            x2="bin_end:Q",
            y=alt.Y("contracts:Q", title="Contracts"),
            tooltip=[
                alt.Tooltip("bin_start:Q", title="From %", format=".1f"),
                alt.Tooltip("bin_end:Q", title="To %", format=".1f"),
                alt.Tooltip("contracts:Q", title="Contracts", format=","),
            ],
        ),
        height=230,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec


def solicitation_procedure_chart_spec(proc_rollup: pd.DataFrame) -> dict[str, Any]:
    if proc_rollup.empty:
        return _empty_chart_spec("No procedure breakdown (dataset may be empty).")
    chart = executive_chart_style(
        alt.Chart(proc_rollup)
        .mark_bar()
        .encode(
            x=alt.X("contracts:Q", title="Contracts"),
            y=alt.Y("solicitation_procedure:N", sort="-x", title=None),
            tooltip=["solicitation_procedure", "contracts"],
        ),
        height=230,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec


def timeline_chart_spec(timeline_df: pd.DataFrame) -> dict[str, Any] | None:
    if timeline_df.empty:
        return None
    chart = executive_chart_style(
        alt.Chart(timeline_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("effective_date:T", title="Timeline date"),
            y=alt.Y("running_total:Q", title="Running contract value", axis=alt.Axis(format="$,.0f")),
            tooltip=[
                "time_detail",
                "label",
                alt.Tooltip("running_total:Q", format="$,.0f"),
                alt.Tooltip("amendment_added:Q", format="$,.0f"),
            ],
        ),
        height=245,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec
