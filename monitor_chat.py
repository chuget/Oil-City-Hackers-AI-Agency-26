"""
Groq-powered Q&A over the current ProcureIntel contract dataset.

Public functions:
- chat_config_present(): is GROQ_API_KEY set?
- answer_question(messages, filters): returns assistant text for a list of chat messages

Design (Option 1, simple Q&A):
- We summarize the in-scope dataset (KPIs, dept rollup, top contracts) and inject
  it as a system context block. The model answers strictly from that context.
- We do NOT pass the entire 27k row table. The model sees aggregates + top-N rows.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from monitor_data_platform import LANE_META, query_lane_aggregates


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
TOP_N_CONTRACTS = 25
TOP_N_DEPARTMENTS = 12
MAX_HISTORY = 12


def _groq_ssl_context() -> ssl.SSLContext:
    """HTTPS to Groq: use a reliable CA bundle (macOS Python often lacks one in the default chain)."""
    flag = (os.environ.get("GROQ_SSL_VERIFY") or "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        # Last resort only (e.g. broken corporate proxy); traffic is not authenticated to the server.
        return ssl._create_unverified_context()

    cafile = (os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE") or "").strip()
    if cafile and Path(cafile).is_file():
        return ssl.create_default_context(cafile=cafile)

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def chat_config_present() -> bool:
    return bool((os.environ.get("GROQ_API_KEY") or "").strip())


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v)


def _coerce_numeric_contract_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Postgres NUMERIC often arrives as Decimal; float math (e.g. * 100.0) must not mix types."""
    out = frame.copy()
    for col in ("original_value", "amendment_value", "current_value", "amendment_ratio"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _summarize_dataset(
    min_original: float,
    department: str,
    procedure: str,
    dataset: str = "contracts",
) -> dict[str, Any]:
    """SQL-backed summary for the active data lane (no full-table load)."""
    lane = dataset if dataset in LANE_META else "contracts"
    try:
        agg = query_lane_aggregates(lane, min_original, department, procedure, TOP_N_CONTRACTS)
    except Exception as exc:
        return {
            "load_source": "database",
            "rows_total": 0,
            "rows_in_scope": 0,
            "summary_text": f"Could not query warehouse: {exc}",
        }

    if agg.get("reason") == "lane_unavailable":
        return {
            "load_source": "database",
            "rows_total": 0,
            "rows_in_scope": 0,
            "summary_text": agg.get("message", "Lane unavailable."),
        }

    kpis_raw = agg.get("kpis") or {}
    rows_in_lane = int(agg.get("rows_in_lane", 0))
    ranked = agg.get("ranked", pd.DataFrame())
    if not isinstance(ranked, pd.DataFrame):
        ranked = pd.DataFrame(ranked)

    if ranked.empty and rows_in_lane == 0:
        return {
            "load_source": "database",
            "rows_total": rows_in_lane,
            "rows_in_scope": 0,
            "summary_text": "No records match the active filters in this lane.",
        }

    ranked = _coerce_numeric_contract_columns(ranked.head(TOP_N_CONTRACTS))
    dept_rollup = agg.get("dept_rollup", pd.DataFrame())
    if not isinstance(dept_rollup, pd.DataFrame):
        dept_rollup = pd.DataFrame(dept_rollup)

    kpis = {
        "contracts_in_scope": rows_in_lane,
        "ratio_gt_25_pct": int(kpis_raw.get("ratio_gt_25", 0)),
        "ratio_gt_100_pct": int(kpis_raw.get("ratio_gt_100", 0)),
        "ratio_gt_300_pct": int(kpis_raw.get("ratio_gt_300", 0)),
    }

    top_depts = []
    for _, r in dept_rollup.head(TOP_N_DEPARTMENTS).iterrows():
        top_depts.append(
            {
                "department": _safe_str(r.get("department")),
                "contracts": int(r.get("contracts", 0)),
                "flagged": int(r.get("flagged", 0)),
                "avg_ratio_pct": float(r.get("avg_ratio", 0) or 0) * 100.0,
            }
        )

    contract_rows = []
    for _, r in ranked.iterrows():
        contract_rows.append(
            {
                "reference_number": _safe_str(r.get("reference_number")),
                "vendor": _safe_str(r.get("vendor_name")),
                "department": _safe_str(r.get("department")),
                "solicitation_procedure": _safe_str(r.get("solicitation_procedure")),
                "original_value": float(r["original_value"]) if pd.notna(r.get("original_value")) else None,
                "amendment_ratio_pct": float(r["ratio_pct"]) if pd.notna(r.get("ratio_pct")) else None,
            }
        )

    summary_payload = {
        "dataset": lane,
        "dataset_label": LANE_META.get(lane, {}).get("label", lane),
        "filters": {
            "min_original": float(min_original),
            "department": department,
            "procedure": procedure,
        },
        "kpis": kpis,
        "top_departments": top_depts,
        "top_contracts_by_ratio": contract_rows,
    }

    return {
        "load_source": "database",
        "rows_total": rows_in_lane,
        "rows_in_scope": rows_in_lane,
        "summary_payload": summary_payload,
    }


def _system_prompt(summary: dict[str, Any]) -> str:
    return (
        "You are ProcureIntel Assistant. You help users explore Agency 2026 government data lanes "
        "(federal contracts, federal grants, Alberta procurement, CRA charity funding, cross-linked entities).\n\n"
        "RULES:\n"
        "1. Answer only using the structured DATASET_CONTEXT below. If the data does not contain "
        "the answer, say so clearly.\n"
        "2. Never accuse a vendor or department of wrongdoing. A high amendment ratio is a SIGNAL "
        "for review, not proof of misconduct. Avoid the word 'fraud'.\n"
        "3. Use plain language. When you cite a contract, include the reference number, vendor, "
        "department, and amendment ratio %.\n"
        "4. Keep answers short and structured (bullet points, short paragraphs). Round currency "
        "to whole dollars and ratios to 1 decimal.\n"
        "5. Do NOT invent contracts that are not in DATASET_CONTEXT. If the user asks about something "
        "outside the dataset, explain that.\n\n"
        "DATASET_CONTEXT (JSON):\n"
        + json.dumps(summary.get("summary_payload", {}), default=str)
        + f"\n\nDataset note: {summary.get('rows_in_scope', 0)} contracts are in scope after filters, "
        f"out of {summary.get('rows_total', 0)} total. Source: {summary.get('load_source', 'unknown')}."
    )


def _sanitize_history(messages: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in list(messages)[-MAX_HISTORY:]:
        role = str(m.get("role", "")).lower()
        content = str(m.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if len(content) > 4000:
            content = content[:4000]
        out.append({"role": role, "content": content})
    return out


def answer_question(
    messages: Iterable[dict[str, Any]],
    *,
    min_original: float = 10_000.0,
    department: str = "(all)",
    procedure: str = "(all)",
    dataset: str = "contracts",
    model: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    if not chat_config_present():
        return {
            "ok": False,
            "error": "GROQ_API_KEY is not set on the server. Add it to .env and restart.",
        }

    history = _sanitize_history(messages)
    if not history or history[-1]["role"] != "user":
        return {"ok": False, "error": "No user message provided."}

    summary = _summarize_dataset(min_original, department, procedure, dataset)
    chat_messages = [{"role": "system", "content": _system_prompt(summary)}] + history

    body = {
        "model": model or DEFAULT_MODEL,
        "messages": chat_messages,
        "temperature": temperature,
        "max_tokens": 700,
    }
    req = urllib.request.Request(
        GROQ_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY'].strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        ctx = _groq_ssl_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        return {
            "ok": False,
            "error": f"Groq HTTP {e.code}: {err_body[:400]}",
        }
    except Exception as e:
        return {"ok": False, "error": f"Chat request failed: {e}"}

    try:
        text = data["choices"][0]["message"]["content"].strip()
    except Exception:
        return {"ok": False, "error": "Unexpected Groq response shape."}

    return {
        "ok": True,
        "reply": text,
        "model": body["model"],
        "rows_in_scope": summary.get("rows_in_scope", 0),
        "rows_total": summary.get("rows_total", 0),
        "load_source": summary.get("load_source", ""),
    }
