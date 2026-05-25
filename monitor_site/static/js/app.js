/* global vegaEmbed */

(function () {
  const $ = (id) => document.getElementById(id);
  const THEME_KEY = "procureintel-theme";
  const pageEl = document.querySelector(".page");

  const fmtMoney = (n) =>
    n == null || Number.isNaN(Number(n))
      ? "—"
      : new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD", maximumFractionDigits: 0 }).format(
          Number(n)
        );

  const verdictClass = (v) => {
    const x = String(v || "").toUpperCase();
    if (x === "PASS") return "badge badge-pass";
    if (x === "CAUTION") return "badge badge-caution";
    if (x === "FAIL") return "badge badge-fail";
    if (x === "HOLD") return "badge badge-hold";
    if (x === "PENDING") return "badge badge-pending";
    return "badge badge-neutral";
  };

  const claimClass = (c) => {
    const x = String(c || "").toUpperCase();
    if (x === "CLEARED") return "badge badge-claim-cleared";
    if (x === "FLAGGED") return "badge badge-claim-flagged";
    if (x === "INVESTIGATED") return "badge badge-claim-investigated";
    if (x === "CRITICAL") return "badge badge-claim-critical";
    return "badge badge-neutral";
  };

  const chartViews = {};

  async function embedChart(key, el, spec) {
    if (chartViews[key]) {
      try {
        chartViews[key].finalize();
      } catch (_) {
        /* ignore */
      }
      chartViews[key] = null;
    }
    el.innerHTML = "";
    if (!spec) return;
    try {
      const boxWidth = Math.floor(el.getBoundingClientRect().width);
      const chartSpec = {
        ...spec,
        autosize: { type: "fit", contains: "padding", resize: true },
      };
      if (boxWidth > 0) {
        chartSpec.width = boxWidth;
      } else {
        chartSpec.width = "container";
      }
      chartViews[key] = await vegaEmbed(el, chartSpec, {
        actions: false,
        renderer: "svg",
        defaultStyle: false,
      });
      const view = chartViews[key]?.view;
      if (view && typeof view.resize === "function") {
        view.resize().run();
      }
    } catch (err) {
      console.error(err);
      el.textContent = "Chart could not be rendered.";
    }
  }

  function fillSelect(sel, options, current) {
    const prev = current != null ? current : sel.value;
    sel.innerHTML = "";
    for (const opt of options) {
      const o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      sel.appendChild(o);
    }
    if (options.includes(prev)) sel.value = prev;
  }

  function renderDeptTable(rows) {
    const tb = $("dept-table").querySelector("tbody");
    tb.innerHTML = "";
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(r.department)}</td>
        <td class="num">${Number(r.contracts).toLocaleString()}</td>
        <td class="num">${Number(r.flagged).toLocaleString()}</td>
        <td class="num">${Number(r.avg_ratio).toFixed(2)}</td>
        <td class="num">${Number(r.max_ratio).toFixed(2)}</td>`;
      tb.appendChild(tr);
    }
  }

  function renderRankedTable(rows, selectedRef) {
    const tb = $("ranked-table").querySelector("tbody");
    tb.innerHTML = "";
    for (const r of rows) {
      const ref = String(r.reference_number);
      const tr = document.createElement("tr");
      tr.className = "row-clickable" + (ref === selectedRef ? " row-selected" : "");
      tr.title = "Click to investigate this contract";
      tr.innerHTML = `
        <td>${escapeHtml(ref)}</td>
        <td>${escapeHtml(String(r.vendor_name ?? ""))}</td>
        <td>${escapeHtml(String(r.department ?? ""))}</td>
        <td class="num">${fmtMoney(r.original_value)}</td>
        <td class="num">${fmtMoney(r.amendment_value)}</td>
        <td class="num">${fmtMoney(r.current_value)}</td>
        <td class="num">${Number(r.ratio_pct).toFixed(1)}%</td>
        <td class="num">${Number(r.ratio_x).toFixed(2)}x</td>
        <td>${escapeHtml(String(r.solicitation_procedure ?? ""))}</td>`;
      tr.addEventListener("click", () => selectContract(ref));
      tb.appendChild(tr);
    }
  }

  function selectContract(ref) {
    if (!ref) return;
    $("contract-select").value = ref;
    loadDashboard(true);
    const sec3 = document.getElementById("sec3");
    if (sec3) {
      sec3.closest(".section-shell")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildDashboardUrl(includeSelection) {
    const params = new URLSearchParams();
    params.set("dataset", $("filter-dataset")?.value || "contracts");
    params.set("min_original", $("min-original").value || "10000");
    params.set("department", $("filter-department").value || "(all)");
    params.set("procedure", $("filter-procedure").value || "(all)");
    if (includeSelection) {
      const ref = $("contract-select").value;
      if (ref) params.set("selected_ref", ref);
    }
    return "/api/dashboard?" + params.toString();
  }

  async function loadCensus() {
    const banner = $("warehouse-banner");
    const stats = $("warehouse-stats");
    const note = $("warehouse-note");
    if (!banner || window.location.protocol === "file:") return;

    try {
      const res = await fetch("/api/data/census");
      const data = await res.json();
      if (!data.ok) {
        banner.hidden = false;
        stats.textContent = "Connect DB_CONNECTION_STRING or DATABASE_URL to the Agency 2026 warehouse (~23M rows).";
        note.textContent = data.message || "";
        return;
      }
      const total = Number(data.total_estimate || 0);
      const cra = Number(data.schema_totals?.cra || 0);
      const fed = Number(data.schema_totals?.fed || 0);
      const ab = Number(data.schema_totals?.ab || 0);
      const general = Number(data.schema_totals?.general || 0);
      banner.hidden = false;
      stats.textContent = `~${total.toLocaleString()} rows estimated in warehouse · CRA ~${cra.toLocaleString()} · FED ~${fed.toLocaleString()} · AB ~${ab.toLocaleString()} · general ~${general.toLocaleString()}`;
      note.textContent = data.note || "";
      const sel = $("filter-dataset");
      if (sel && data.lanes) {
        const prev = sel.value;
        sel.innerHTML = "";
        for (const lane of data.lanes) {
          const o = document.createElement("option");
          o.value = lane.id;
          o.textContent = lane.available ? lane.label : `${lane.label} (unavailable)`;
          o.disabled = !lane.available;
          sel.appendChild(o);
        }
        if ([...sel.options].some((o) => o.value === prev && !o.disabled)) sel.value = prev;
      }
    } catch (e) {
      console.warn("Census load failed", e);
    }
  }

  let filterEventLock = false;

  function setLoading(loading) {
    if (pageEl) pageEl.classList.toggle("is-loading", loading);
  }

  function initTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = stored === "dark" || stored === "light" ? stored : prefersDark ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    updateThemeToggleLabel();
  }

  function updateThemeToggleLabel() {
    const btn = $("theme-toggle");
    if (!btn) return;
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    const label = btn.querySelector(".theme-toggle__label");
    if (label) label.textContent = dark ? "Light" : "Dark";
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  }

  function setBanners(clearApi) {
    const fb = $("file-banner");
    const ae = $("api-error");
    if (window.location.protocol === "file:") {
      fb.hidden = false;
      fb.textContent =
        "This page was opened as a file. Run the server and open http://127.0.0.1:8765 instead — otherwise contract data cannot load.";
    } else {
      fb.hidden = true;
      fb.textContent = "";
    }
    if (clearApi) {
      ae.hidden = true;
      ae.textContent = "";
    }
  }

  function setStatusPills(data) {
    const row = $("status-row");
    const ps = $("pill-source");
    const pl = $("pill-lane");
    const pr = $("pill-rows");
    if (!data || data.load_source === undefined) {
      row.hidden = true;
      return;
    }
    row.hidden = false;
    if (data.load_source === "database") {
      ps.className = "pill pill--db";
      ps.textContent = "Source: Agency 2026 Postgres";
    } else {
      ps.className = "pill pill--csv";
      ps.textContent = data.database_config_present
        ? "Source: CSV fallback"
        : "Source: CSV fallback — no DB URL configured";
    }
    if (pl) {
      pl.className = "pill pill--lane";
      pl.textContent = `Lane: ${data.dataset_label || data.dataset || "contracts"}`;
    }
    pr.className = "pill pill--rows";
    const inLane = Number(data.rows_in_lane ?? data.rows_loaded ?? 0);
    const returned = Number(data.rows_returned_ranked ?? inLane);
    pr.textContent =
      returned < inLane
        ? `In scope: ${inLane.toLocaleString()} · top ${returned.toLocaleString()}`
        : `In scope: ${inLane.toLocaleString()}`;
  }

  async function loadDashboard(includeSelection) {
    const cap = $("data-caption");
    const ae = $("api-error");
    setBanners(true);
    ae.hidden = true;
    ae.textContent = "";

    if (window.location.protocol === "file:") {
      cap.textContent = "";
      return;
    }

    cap.textContent = "Loading…";
    setLoading(true);
    let data;
    try {
      const res = await fetch(buildDashboardUrl(includeSelection));
      const raw = await res.text();
      try {
        data = JSON.parse(raw);
      } catch {
        ae.hidden = false;
        ae.textContent = "Server returned a non-JSON response. Is uvicorn running from the app folder?";
        cap.textContent = "";
        setLoading(false);
        return;
      }
      if (!res.ok) {
        ae.hidden = false;
        ae.textContent =
          (data && (data.error || data.detail)) ||
          `Request failed (${res.status}). Check DB credentials, PGSSLMODE (try prefer), and .env beside the app.`;
        cap.textContent = "";
        setStatusPills(null);
        setLoading(false);
        return;
      }
    } catch (e) {
      cap.textContent = "";
      ae.hidden = false;
      ae.textContent = "Network error — is the FastAPI server running? (" + String(e) + ")";
      console.error(e);
      setStatusPills(null);
      setLoading(false);
      return;
    }

    const srcLabel = data.load_source === "database" ? "Agency 2026 warehouse" : "CSV fallback";
    const laneLabel = data.dataset_label || data.dataset || "contracts";
    cap.textContent = `${srcLabel} · ${laneLabel} · ${Number(data.rows_in_lane ?? data.rows_loaded ?? 0).toLocaleString()} records in scope`;
    const rn = $("ranked-note");
    if (rn) {
      if (data.ranked_note) {
        rn.hidden = false;
        rn.textContent = data.ranked_note;
      } else {
        rn.hidden = true;
        rn.textContent = "";
      }
    }
    setStatusPills(data);
    if (!data.database_config_present) {
      ae.hidden = false;
      ae.textContent =
        "Set DB_CONNECTION_STRING or DATABASE_URL to the hackathon unified Postgres (~23M rows). Without it, only a small CSV sample is available.";
    }

    if (!filterEventLock) {
      filterEventLock = true;
      fillSelect($("filter-department"), data.filter_departments || ["(all)"], $("filter-department").value);
      fillSelect($("filter-procedure"), data.filter_procedures || ["(all)"], $("filter-procedure").value);
      filterEventLock = false;
    }

    $("kpi-scanned").textContent = Number(data.kpis?.contracts_scanned ?? 0).toLocaleString();
    $("kpi-25").textContent = Number(data.kpis?.ratio_gt_25 ?? 0).toLocaleString();
    $("kpi-100").textContent = Number(data.kpis?.ratio_gt_100 ?? 0).toLocaleString();
    $("kpi-300").textContent = Number(data.kpis?.ratio_gt_300 ?? 0).toLocaleString();

    $("dept-context-note").hidden = !data.department_note;

    renderDeptTable(data.dept_rollup || []);
    await embedChart("dept", $("chart-dept"), data.chart_dept);
    await embedChart("hist", $("chart-hist"), data.chart_hist);
    await embedChart("proc", $("chart-proc"), data.chart_proc);

    const empty = !data.ok || (data.ranked && data.ranked.length === 0);
    const warn = $("empty-ranked");
    warn.hidden = !empty;
    $("ranked-wrap").hidden = empty;
    $("contract-select").closest(".contract-select-wrap").hidden = empty;
    document.getElementById("sec3").closest(".section-shell").style.opacity = empty ? "0.45" : "1";
    document.getElementById("sec4").closest(".section-shell").style.opacity = empty ? "0.45" : "1";

    if (empty) {
      if (data.reason === "no_data") {
        warn.textContent =
          data.message ||
          "No contract rows were returned. Configure the database URL or ensure data/contracts.csv exists.";
      } else if (data.reason === "no_contracts") {
        warn.textContent = ["No contracts match the current filter set.", data.hint].filter(Boolean).join(" ");
      } else {
        warn.textContent = data.message || "No rows to display.";
      }
      $("ranked-table").querySelector("tbody").innerHTML = "";
      $("contract-select").innerHTML = "";
      await embedChart("timeline", $("chart-timeline"), null);
      setLoading(false);
      return;
    }

    const selectedRef = String(data.selected_ref || data.ranked[0]?.reference_number || "");
    renderRankedTable(data.ranked, selectedRef);
    const refs = data.ranked.map((r) => String(r.reference_number));
    filterEventLock = true;
    fillSelect($("contract-select"), refs, data.selected_ref);
    filterEventLock = false;

    const p = data.profile || {};
    $("profile-list").innerHTML = `
      <li><strong>Reference:</strong> ${escapeHtml(String(p.reference_number ?? ""))}</li>
      <li><strong>Vendor:</strong> ${escapeHtml(String(p.vendor_name ?? ""))}</li>
      <li><strong>Department:</strong> ${escapeHtml(String(p.department ?? ""))}</li>
      <li><strong>Date:</strong> ${escapeHtml(String(p.contract_date ?? ""))}</li>
      <li><strong>Solicitation procedure:</strong> ${escapeHtml(String(p.solicitation_procedure ?? ""))}</li>
      <li><strong>Description:</strong> ${escapeHtml(String(p.description ?? ""))}</li>`;

    const vs = data.value_summary || {};
    $("value-summary").innerHTML = `
      <li><strong>Original:</strong> ${escapeHtml(vs.original || "—")}</li>
      <li><strong>Amendments:</strong> ${escapeHtml(vs.amendments || "—")}</li>
      <li><strong>Current:</strong> ${escapeHtml(vs.current || "—")}</li>
      <li><strong>Amendment ratio:</strong> ${escapeHtml(vs.amendment_ratio || "—")}</li>`;

    const chip = $("timeline-chip");
    if (data.timeline_source === "actual") {
      chip.textContent = "Timeline source: Actual contract history";
    } else if (data.timeline_source === "synthetic") {
      chip.textContent = "Timeline source: Synthetic fallback";
    } else {
      chip.textContent = "";
    }

    await embedChart("timeline", $("chart-timeline"), data.chart_timeline);

    const gl = $("gate-list");
    gl.innerHTML = "";
    for (const g of data.gates || []) {
      const div = document.createElement("div");
      div.className = "gate-row";
      div.innerHTML = `<strong>${escapeHtml(g.gate)}:</strong> <span class="${verdictClass(g.verdict)}">${escapeHtml(
        g.verdict
      )}</span> — ${escapeHtml(g.rationale)}`;
      gl.appendChild(div);
    }

    $("claim-line").innerHTML = `<strong>Claim validity:</strong> <span class="${claimClass(data.claim)}">${escapeHtml(
      data.claim || ""
    )}</span>`;

    const ev = $("evidence-list");
    ev.innerHTML = "";
    for (const item of data.evidence || []) {
      const li = document.createElement("li");
      li.textContent = item;
      ev.appendChild(li);
    }

    const pc = $("pc-rules");
    pc.innerHTML = "";
    for (const item of data.pc_rules || []) {
      const li = document.createElement("li");
      li.textContent = item;
      pc.appendChild(li);
    }

    setLoading(false);
  }

  function debounce(fn, ms) {
    let t;
    return function () {
      clearTimeout(t);
      t = setTimeout(fn, ms);
    };
  }

  $("filter-dataset")?.addEventListener("change", () => loadDashboard(false));
  $("filter-department").addEventListener("change", () => loadDashboard(false));
  $("filter-procedure").addEventListener("change", () => loadDashboard(false));
  $("min-original").addEventListener("input", debounce(() => loadDashboard(false), 350));
  $("contract-select").addEventListener("change", () => loadDashboard(true));

  const themeBtn = $("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const dark = document.documentElement.getAttribute("data-theme") === "dark";
      const next = dark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem(THEME_KEY, next);
      updateThemeToggleLabel();
    });
  }

  initTheme();
  loadCensus().then(() => loadDashboard(false));
})();
