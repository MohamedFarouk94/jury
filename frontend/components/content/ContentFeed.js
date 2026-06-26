import { sendContent, fetchContents, fetchContent } from "../../services/api.js";
import { verdictColor, violationLabel } from "../../utils/verdict.js";

export async function renderContentFeed(container, policy, getRules) {
  let contents = await fetchContents(policy.id);

  // Poll pending contents every 3 seconds
  let pollInterval = null;

  function hasPending() {
    return contents.some((c) => c.verdict === null);
  }

  function startPolling() {
    if (pollInterval) return;
    pollInterval = setInterval(async () => {
      const pending = contents.filter((c) => c.verdict === null);
      if (pending.length === 0) {
        clearInterval(pollInterval);
        pollInterval = null;
        return;
      }
      for (const c of pending) {
        const updated = await fetchContent(c.id).catch(() => null);
        if (updated && updated.verdict !== null) {
          const idx = contents.findIndex((x) => x.id === c.id);
          if (idx !== -1) contents[idx] = updated;
          updateContentBox(updated);
        }
      }
    }, 3000);
  }

  function updateContentBox(content) {
    const box = document.querySelector(`.content-box[data-id="${content.id}"]`);
    if (!box) return;
    const rules = getRules();
    const color = verdictColor(content.verdict, rules);
    box.className = `content-box verdict-${color}`;
    const badge = box.querySelector(".verdict-badge");
    if (badge) {
      badge.textContent = color === "pending" ? "Pending…" : colorLabel(color);
      badge.className = `verdict-badge badge-${color}`;
    }
  }

  function colorLabel(color) {
    return { green: "Compliant", yellow: "Review needed", red: "Violation", pending: "Pending…" }[color] || "";
  }

  function openVerdictModal(content) {
    const rules = getRules();
    const verdict = content.verdict;
    if (!verdict) return;

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";

    const ruleRows = rules
      .map((r) => {
        const level = verdict[String(r.id)] ?? 0;
        const color = level === 0 ? "green" : level === 1 ? "yellow" : "red";
        return `
        <div class="verdict-row">
          <div class="verdict-rule-name">${escapeHtml(r.name)}</div>
          <div class="verdict-level verdict-level-${color}">${violationLabel(level)}</div>
        </div>`;
      })
      .join("");

    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <h3>Verdict Details</h3>
          <button class="btn-icon modal-close">✕</button>
        </div>
        <div class="modal-content">
          <div class="content-preview">${escapeHtml(content.text)}</div>
          <div class="verdict-rules">${ruleRows}</div>
          ${verdict.details ? `<div class="verdict-details"><strong>Reasoning:</strong> ${escapeHtml(verdict.details)}</div>` : ""}
        </div>
      </div>`;

    overlay.querySelector(".modal-close").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
    document.body.appendChild(overlay);
  }

  function renderBox(content) {
    const rules = getRules();
    const color = verdictColor(content.verdict, rules);
    const div = document.createElement("div");
    div.className = `content-box verdict-${color}`;
    div.dataset.id = content.id;

    const ts = new Date(content.created_at).toLocaleString();
    div.innerHTML = `
      <div class="content-box-body">
        <p class="content-text">${escapeHtml(content.text)}</p>
        <div class="content-meta">
          <span class="content-time">${ts}</span>
          <span class="verdict-badge badge-${color}">${colorLabel(color)}</span>
        </div>
      </div>`;

    if (content.verdict) {
      div.style.cursor = "pointer";
      div.addEventListener("click", () => openVerdictModal(content));
    }

    return div;
  }

  function render() {
    container.innerHTML = `
      <div class="feed-header">
        <h3>${escapeHtml(policy.name)}</h3>
        ${policy.description ? `<p class="policy-desc-sub">${escapeHtml(policy.description)}</p>` : ""}
      </div>
      <div class="content-list" id="content-list"></div>
      <div class="content-input-area">
        <textarea id="content-input" placeholder="Paste content to check against this policy…" rows="3"></textarea>
        <div class="input-row">
          <p id="feed-error" class="form-error hidden"></p>
          <button class="btn btn-primary" id="send-content-btn">Check content</button>
        </div>
      </div>`;

    const list = container.querySelector("#content-list");
    contents.forEach((c) => list.appendChild(renderBox(c)));
    list.scrollTop = list.scrollHeight;

    if (hasPending()) startPolling();

    container.querySelector("#send-content-btn").addEventListener("click", async () => {
      const input = container.querySelector("#content-input");
      const errEl = container.querySelector("#feed-error");
      const text = input.value.trim();
      if (!text) {
        errEl.textContent = "Content cannot be empty.";
        errEl.classList.remove("hidden");
        return;
      }
      errEl.classList.add("hidden");
      input.disabled = true;
      container.querySelector("#send-content-btn").disabled = true;

      try {
        const content = await sendContent(policy.id, text);
        contents.push(content);
        const box = renderBox(content);
        list.appendChild(box);
        list.scrollTop = list.scrollHeight;
        input.value = "";
        startPolling();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove("hidden");
      } finally {
        input.disabled = false;
        container.querySelector("#send-content-btn").disabled = false;
      }
    });
  }

  render();

  // Return cleanup so we can stop polling when switching policies
  return () => {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = null;
  };
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
