/* global vegaEmbed */

(function () {
  const $ = (id) => document.getElementById(id);

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
      chartViews[key] = await vegaEmbed(el, spec, {
        actions: false,
        renderer: "svg",
        defaultStyle: false,
        theme: "quartz",
      });
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

  function renderRankedTable(rows) {
    const tb = $("ranked-table").querySelector("tbody");
    tb.innerHTML = "";
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(String(r.reference_number))}</td>
        <td>${escapeHtml(String(r.vendor_name ?? ""))}</td>
        <td>${escapeHtml(String(r.department ?? ""))}</td>
        <td class="num">${fmtMoney(r.original_value)}</td>
        <td class="num">${fmtMoney(r.amendment_value)}</td>
        <td class="num">${fmtMoney(r.current_value)}</td>
        <td class="num">${Number(r.ratio_pct).toFixed(1)}%</td>
        <td class="num">${Number(r.ratio_x).toFixed(2)}x</td>
        <td>${escapeHtml(String(r.solicitation_procedure ?? ""))}</td>`;
      tb.appendChild(tr);
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
    params.set("min_original", $("min-original").value || "10000");
    params.set("department", $("filter-department").value || "(all)");
    params.set("procedure", $("filter-procedure").value || "(all)");
    if (includeSelection) {
      const ref = $("contract-select").value;
      if (ref) params.set("selected_ref", ref);
    }
    return "/api/dashboard?" + params.toString();
  }

  let filterEventLock = false;

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
    const pr = $("pill-rows");
    if (!data || data.load_source === undefined) {
      row.hidden = true;
      return;
    }
    row.hidden = false;
    if (data.load_source === "database") {
      ps.className = "pill pill--db";
      ps.textContent = "Source: Live database";
    } else {
      ps.className = "pill pill--csv";
      ps.textContent = data.database_config_present
        ? "Source: CSV fallback"
        : "Source: CSV fallback — no DB_CONNECTION_STRING or DATABASE_URL found";
    }
    pr.className = "pill pill--rows";
    pr.textContent = `Rows loaded: ${Number(data.rows_loaded || 0).toLocaleString()}`;
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
        return;
      }
      if (!res.ok) {
        ae.hidden = false;
        ae.textContent =
          (data && (data.error || data.detail)) ||
          `Request failed (${res.status}). Check DB credentials, PGSSLMODE (try prefer), and .env beside the app.`;
        cap.textContent = "";
        setStatusPills(null);
        return;
      }
    } catch (e) {
      cap.textContent = "";
      ae.hidden = false;
      ae.textContent = "Network error — is the FastAPI server running? (" + String(e) + ")";
      console.error(e);
      setStatusPills(null);
      return;
    }

    const srcLabel = data.load_source === "database" ? "Database" : "CSV fallback";
    cap.textContent = `Data source: ${srcLabel} | Rows loaded: ${Number(data.rows_loaded || 0).toLocaleString()}`;
    setStatusPills(data);
    if (data.load_source === "csv" && data.database_config_present === false) {
      ae.hidden = false;
      ae.textContent =
        "Database is not linked: no DB_CONNECTION_STRING or DATABASE_URL was found in the server environment, .env, or web/.env. The dashboard is showing local CSV sample data.";
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
      return;
    }

    renderRankedTable(data.ranked);
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
  }

  function debounce(fn, ms) {
    let t;
    return function () {
      clearTimeout(t);
      t = setTimeout(fn, ms);
    };
  }

  $("filter-department").addEventListener("change", () => loadDashboard(false));
  $("filter-procedure").addEventListener("change", () => loadDashboard(false));
  $("min-original").addEventListener("input", debounce(() => loadDashboard(false), 350));
  $("contract-select").addEventListener("change", () => loadDashboard(true));

  loadDashboard(false);
})();
