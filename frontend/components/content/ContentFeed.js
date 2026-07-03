import { sendContent, fetchContents, fetchContent } from "../../services/api.js";
import { verdictColor, violationLabel } from "../../utils/verdict.js";

export async function renderContentFeed(container, policy, getRules) {
  let contents = await fetchContents(policy.id);

  let pollInterval = null;
  const fetchFailures = new Map(); // content id -> consecutive failure count
  const MAX_FETCH_FAILURES = 5;

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
          fetchFailures.delete(c.id);
          const idx = contents.findIndex((x) => x.id === c.id);
          if (idx !== -1) contents[idx] = updated;
          updateContentBox(updated);
        } else if (!updated) {
          // Network/API failure fetching this content's status — track it
          // rather than polling forever with no feedback to the user.
          const failures = (fetchFailures.get(c.id) || 0) + 1;
          fetchFailures.set(c.id, failures);
          if (failures >= MAX_FETCH_FAILURES) {
            fetchFailures.delete(c.id);
            const errored = {
              ...c,
              verdict: { error: "fetch_failed", details: "Couldn't reach the server to retrieve this verdict. It may still complete — try refreshing later." },
            };
            const idx = contents.findIndex((x) => x.id === c.id);
            if (idx !== -1) contents[idx] = errored;
            updateContentBox(errored);
          }
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
      badge.textContent = colorLabel(color);
      badge.className = `verdict-badge badge-${color}`;
    }
    box.style.cursor = "pointer";
    box.addEventListener("click", () => openVerdictModal(content));
  }
 

  function colorLabel(color) {
    return { green: "Compliant", yellow: "Review needed", red: "Violation", error: "Error", pending: "Pending…" }[color] || "";
  }

  function openVerdictModal(content) {
    const rules = getRules();
    const verdict = content.verdict;
    if (!verdict) return;

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";

    if (verdict.error) {
      overlay.innerHTML = `
        <div class="modal">
          <div class="modal-header">
            <h3>Verdict Unavailable</h3>
            <button class="btn-icon modal-close">✕</button>
          </div>
          <div class="modal-content">
            <div class="content-preview">${escapeHtml(content.text)}</div>
            <div class="verdict-error-box">
              <strong>⚠ Moderation failed</strong>
              <p>${escapeHtml(verdict.details || "The AI moderation service was unable to process this content.")}</p>
            </div>
          </div>
        </div>`;
      overlay.querySelector(".modal-close").addEventListener("click", () => overlay.remove());
      overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
      document.body.appendChild(overlay);
      return;
    }

    const ruleRows = rules
      .map((r) => {
        // Verdict keys are policy_rule_index (1, 2, 3...) as strings
        const level = verdict[String(r.policy_rule_index)] ?? 0;
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

  function updateSendButton() {
    const btn = container.querySelector("#send-content-btn");
    const input = container.querySelector("#content-input");
    const hint = container.querySelector("#no-rules-hint");
    if (!btn) return;
    const rules = getRules();
    const hasRules = rules.length > 0;
    btn.disabled = !hasRules;
    if (input) input.disabled = !hasRules;
    if (hint) hint.classList.toggle("hidden", hasRules);
  }

  function render() {
    const rules = getRules();
    const hasRules = rules.length > 0;

    container.innerHTML = `
      <div class="feed-header">
        <h3>${escapeHtml(policy.name)}</h3>
        ${policy.description ? `<p class="policy-desc-sub">${escapeHtml(policy.description)}</p>` : ""}
      </div>
      <div class="content-list" id="content-list"></div>
      <div class="content-input-area">
        <textarea id="content-input" placeholder="Paste content to check against this policy…" rows="3" ${!hasRules ? "disabled" : ""}></textarea>
        <div class="input-row">
          <p id="feed-error" class="form-error hidden"></p>
          <button class="btn btn-primary" id="send-content-btn" ${!hasRules ? "disabled" : ""}>Check content</button>
        </div>
        <p id="no-rules-hint" class="form-error ${hasRules ? "hidden" : ""}">
          Add at least one rule to this policy before checking content.
        </p>
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

      // Guard: re-check rules in case they were all deleted after render
      if (getRules().length === 0) {
        errEl.textContent = "Add at least one rule before checking content.";
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
        updateSendButton();
      }
    });
  }

  render();

  // Expose so RulesPanel can call this when rules change
  return {
    cleanup: () => {
      if (pollInterval) clearInterval(pollInterval);
      pollInterval = null;
    },
    onRulesChanged: updateSendButton,
  };
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}