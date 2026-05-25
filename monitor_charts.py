"""Altair charts as Vega-Lite specs for the contract monitor."""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd


def _empty_chart_spec(message: str, height: int = 220) -> dict[str, Any]:
    ch = (
        alt.Chart(pd.DataFrame({"t": [message]}))
        .mark_text(fontSize=13, color="#5c6578", align="left", lineHeight=18)
        .encode(text="t:N", x=alt.value(8), y=alt.value(10))
        .properties(height=height, width="container")
    )
    spec = executive_chart_style(ch, height).to_dict()
    spec["background"] = "transparent"
    return spec


def executive_chart_style(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(
            height=height,
            width="container",
            autosize=alt.AutoSizeParams(type="fit", contains="padding"),
        )
        .configure_axis(
            labelColor="#5c6578",
            titleColor="#5c6578",
            gridColor="#c8d0dc",
            tickColor="#c8d0dc",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_view(stroke="transparent")
        .configure_title(color="#0f172a", fontSize=13)
        .configure_legend(
            labelColor="#5c6578",
            titleColor="#0f172a",
        )
    )


def dept_flagged_chart_spec(dept_rollup: pd.DataFrame) -> dict[str, Any]:
    if dept_rollup.empty:
        return _empty_chart_spec("No department data to chart (dataset may be empty or fully filtered).")
    plot_df = dept_rollup.copy()
    plot_df["department_label"] = plot_df["department"].astype(str).map(
        lambda s: (s[:32] + "…") if len(s) > 35 else s
    )
    n_bars = max(1, len(plot_df))
    chart_height = max(220, min(400, n_bars * 34 + 48))
    chart = executive_chart_style(
        alt.Chart(plot_df)
        .mark_bar(size=18)
        .encode(
            x=alt.X("flagged:Q", title="Flagged count (ratio > 25%)", scale=alt.Scale(nice=True, zero=True)),
            y=alt.Y(
                "department_label:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=120, labelPadding=4),
            ),
            tooltip=[
                alt.Tooltip("department:N", title="Department"),
                alt.Tooltip("contracts:Q", title="Contracts", format=","),
                alt.Tooltip("flagged:Q", title="Flagged", format=","),
                alt.Tooltip("avg_ratio:Q", title="Avg ratio", format=".2f"),
            ],
        ),
        height=chart_height,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec


def histogram_bins_chart_spec(hist_df: pd.DataFrame, x_title: str = "Ratio (%)") -> dict[str, Any]:
    """Pre-aggregated histogram bins from SQL (bin_start, bin_end, contracts)."""
    if hist_df.empty:
        return _empty_chart_spec("No distribution data in scope.", height=200)
    plot_df = hist_df.copy()
    if "bin_end" not in plot_df.columns and "bin_start" in plot_df.columns:
        plot_df["bin_end"] = plot_df["bin_start"] + 25.0
    chart = executive_chart_style(
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X("bin_start:Q", title=x_title, scale=alt.Scale(nice=True)),
            x2=alt.X2("bin_end:Q"),
            y=alt.Y("contracts:Q", title="Records", scale=alt.Scale(nice=True, zero=True)),
            tooltip=[
                alt.Tooltip("bin_start:Q", title="From", format=".1f"),
                alt.Tooltip("bin_end:Q", title="To", format=".1f"),
                alt.Tooltip("contracts:Q", title="Count", format=","),
            ],
        ),
        height=230,
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

    # Focus on non-negative ratios; cap extreme outliers so the axis stays readable.
    if len(ratios) > 1:
        upper = float(min(max(ratios.quantile(0.99), 25), 400))
    else:
        upper = float(max(ratios.iloc[0] * 1.1, 25))
    ratios = ratios[(ratios >= 0) & (ratios <= upper)]
    if ratios.empty:
        return _empty_chart_spec("No non-negative amendment ratios in scope.", height=200)

    bin_count = min(24, max(8, int(ratios.nunique())))
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

    # Drop empty bins so the chart has no visual gaps between bars.
    hist_df = hist_df[hist_df["contracts"] > 0].reset_index(drop=True)
    if hist_df.empty:
        return _empty_chart_spec("No numeric amendment ratios in scope.", height=200)

    chart = executive_chart_style(
        alt.Chart(hist_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "bin_start:Q",
                title="Amendment ratio (%)",
                scale=alt.Scale(domain=[0, upper], nice=False),
            ),
            x2=alt.X2("bin_end:Q"),
            y=alt.Y("contracts:Q", title="Contracts", scale=alt.Scale(nice=True, zero=True)),
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
    plot_df = proc_rollup.copy()
    plot_df["procedure_label"] = plot_df["solicitation_procedure"].astype(str).map(
        lambda s: (s[:40] + "…") if len(s) > 43 else s
    )
    chart = executive_chart_style(
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X("contracts:Q", title="Contracts", scale=alt.Scale(nice=True, zero=True)),
            y=alt.Y(
                "procedure_label:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=260),
            ),
            tooltip=[
                alt.Tooltip("solicitation_procedure:N", title="Procedure"),
                alt.Tooltip("contracts:Q", title="Contracts", format=","),
            ],
        ),
        height=230,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec


def timeline_chart_spec(timeline_df: pd.DataFrame) -> dict[str, Any] | None:
    if timeline_df.empty:
        return None

    tl = timeline_df.copy()
    tl["effective_date"] = pd.to_datetime(tl["effective_date"], errors="coerce")
    tl["running_total"] = pd.to_numeric(tl["running_total"], errors="coerce")
    if "timeline_step" not in tl.columns:
        tl["timeline_step"] = tl.index + 1
    tl = tl.dropna(subset=["effective_date", "running_total"])
    if tl.empty:
        return None

    tl = tl.sort_values(["effective_date", "timeline_step"], na_position="last").reset_index(drop=True)
    # Drop consecutive duplicate points (same date and value) so the line does not redraw flat segments.
    same = (tl["effective_date"] == tl["effective_date"].shift()) & (
        tl["running_total"] == tl["running_total"].shift()
    )
    tl = tl.loc[~same].reset_index(drop=True)
    if tl.empty:
        return None

    chart = executive_chart_style(
        alt.Chart(tl)
        .mark_line(interpolate="step-after", point={"filled": True, "size": 60})
        .encode(
            x=alt.X(
                "effective_date:T",
                title="Timeline date",
                axis=alt.Axis(format="%Y-%m-%d", labelAngle=-25),
            ),
            y=alt.Y(
                "running_total:Q",
                title="Running contract value",
                axis=alt.Axis(format="$,.0f"),
                scale=alt.Scale(nice=True, zero=False),
            ),
            order=alt.Order("timeline_step:Q"),
            tooltip=[
                "time_detail",
                "label",
                alt.Tooltip("running_total:Q", format="$,.0f", title="Running total"),
                alt.Tooltip("amendment_added:Q", format="$,.0f", title="Amendment added"),
            ],
        ),
        height=245,
    )
    spec = chart.to_dict()
    spec["background"] = "transparent"
    return spec
