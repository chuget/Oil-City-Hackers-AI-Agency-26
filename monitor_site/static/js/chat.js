/* ProcureIntel chat assistant (Groq-backed) */
(function () {
  const $ = (id) => document.getElementById(id);

  const fab = $("chat-fab");
  const panel = $("chat-panel");
  const closeBtn = $("chat-close");
  const form = $("chat-form");
  const input = $("chat-input");
  const sendBtn = $("chat-send");
  const messagesEl = $("chat-messages");
  const suggestions = $("chat-suggestions");
  const subEl = $("chat-panel-sub");

  if (!fab || !panel || !form || !input || !messagesEl) return;

  const history = []; // [{role:'user'|'assistant', content:string}]
  let busy = false;

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderMarkdownish(text) {
    const safe = escapeHtml(text);
    return safe
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n\n/g, "<br /><br />")
      .replace(/\n/g, "<br />");
  }

  function appendMessage(role, content, opts = {}) {
    const wrap = document.createElement("div");
    wrap.className = `chat-msg chat-msg--${role}`;
    if (opts.error) wrap.classList.add("chat-msg--error");
    if (opts.thinking) wrap.classList.add("chat-msg--thinking");
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.innerHTML = renderMarkdownish(content);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }

  function setBusy(b) {
    busy = b;
    sendBtn.disabled = b;
    input.disabled = b;
    sendBtn.textContent = b ? "..." : "Send";
  }

  function readFiltersFromDom() {
    const minOriginalEl = document.getElementById("min-original");
    const deptEl = document.getElementById("filter-department");
    const procEl = document.getElementById("filter-procedure");
    const datasetEl = document.getElementById("filter-dataset");
    return {
      min_original: minOriginalEl ? Number(minOriginalEl.value || 10000) : 10000,
      department: deptEl && deptEl.value ? deptEl.value : "(all)",
      procedure: procEl && procEl.value ? procEl.value : "(all)",
      dataset: datasetEl && datasetEl.value ? datasetEl.value : "contracts",
    };
  }

  function openPanel() {
    panel.hidden = false;
    fab.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => panel.classList.add("chat-panel--open"));
    setTimeout(() => input.focus(), 50);
    if (!history.length) {
      appendMessage(
        "assistant",
        "I answer questions about the contracts in your current filter scope only. Try a suggestion below, or ask about departments, ratios, or top-ranked contracts."
      );
    }
  }

  function closePanel() {
    panel.classList.remove("chat-panel--open");
    fab.setAttribute("aria-expanded", "false");
    setTimeout(() => {
      panel.hidden = true;
    }, 180);
  }

  async function sendMessage(userText) {
    if (busy) return;
    const text = String(userText || "").trim();
    if (!text) return;

    appendMessage("user", text);
    history.push({ role: "user", content: text });
    input.value = "";
    setBusy(true);
    const thinking = appendMessage("assistant", "Working on your question…", { thinking: true });

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history,
          filters: readFiltersFromDom(),
        }),
      });
      const raw = await res.text();
      let data;
      try {
        data = JSON.parse(raw);
      } catch {
        thinking.remove();
        const snippet = raw.replace(/\s+/g, " ").trim().slice(0, 280);
        appendMessage(
          "assistant",
          snippet
            ? `Server returned non-JSON (${res.status}). ${snippet}`
            : `Server returned an empty or non-JSON body (HTTP ${res.status}).`,
          { error: true }
        );
        return;
      }
      thinking.remove();
      if (!res.ok || !data.ok) {
        const msg = (data && data.error) || `Request failed (${res.status}).`;
        appendMessage("assistant", msg, { error: true });
        return;
      }
      appendMessage("assistant", data.reply || "(no reply)");
      history.push({ role: "assistant", content: data.reply || "" });
      if (subEl && data.rows_in_scope != null) {
        subEl.textContent = `Scope: ${Number(data.rows_in_scope).toLocaleString()} of ${Number(
          data.rows_total || 0
        ).toLocaleString()} contracts · ${data.load_source || "data"}`;
      }
    } catch (e) {
      thinking.remove();
      appendMessage("assistant", `Network error: ${e}`, { error: true });
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  fab.addEventListener("click", () => {
    if (panel.hidden) openPanel();
    else closePanel();
  });
  closeBtn.addEventListener("click", closePanel);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(input.value);
  });
  if (suggestions) {
    suggestions.addEventListener("click", (e) => {
      const t = e.target.closest("button[data-q]");
      if (!t) return;
      sendMessage(t.dataset.q);
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) closePanel();
  });

  fetch("/api/chat/status")
    .then((r) => r.json())
    .then((s) => {
      if (s && s.enabled) {
        fab.hidden = false;
      } else {
        fab.hidden = true;
      }
    })
    .catch(() => {
      fab.hidden = true;
    });
})();
