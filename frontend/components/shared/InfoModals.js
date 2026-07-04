// Shared About / Contact / API-key modals — used from both AuthPage and
// Dashboard so About/Contact are reachable whether you're logged in or not.
// The API modal is only ever wired up from the Dashboard (it requires auth).

import { fetchApiKeys, createApiKey, revokeApiKey } from "../../services/api.js";

// Minimal line-style SVG icons (24x24, currentColor) — no external requests needed.
const ICONS = {
  email: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>`,
  portfolio: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.7 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.7-3.8-9S9.5 5.6 12 3z"/></svg>`,
  github: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.5 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.19-3.37-1.19-.46-1.2-1.11-1.52-1.11-1.52-.9-.63.07-.62.07-.62 1 .07 1.53 1.05 1.53 1.05.9 1.56 2.36 1.11 2.93.85.09-.66.35-1.11.63-1.37-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.32.1-2.75 0 0 .84-.28 2.75 1.05a9.29 9.29 0 0 1 5 0c1.91-1.33 2.75-1.05 2.75-1.05.55 1.43.2 2.49.1 2.75.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.57 5.06.36.32.68.95.68 1.92 0 1.39-.01 2.5-.01 2.84 0 .28.18.61.69.5A10.26 10.26 0 0 0 22 12.25C22 6.58 17.52 2 12 2z"/></svg>`,
  linkedin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 11v5M8 8v.01M12 16v-3.2c0-1.1.7-1.8 1.75-1.8S15.5 11.7 15.5 12.8V16"/></svg>`,
  x: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.9 3H21l-6.9 7.9L22 21h-6.4l-5-6.5L4.7 21H2.6l7.4-8.5L2 3h6.5l4.5 6 5.9-6z"/></svg>`,
  instagram: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none"/></svg>`,
};

function openModal(title, bodyHtml, extraClass = "") {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal ${extraClass}">
      <div class="modal-header">
        <h3>${title}</h3>
        <button class="btn-icon modal-close">✕</button>
      </div>
      <div class="modal-content">${bodyHtml}</div>
    </div>`;

  overlay.querySelector(".modal-close").addEventListener("click", () => overlay.remove());
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
  document.addEventListener("keydown", function onEsc(e) {
    if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", onEsc); }
  });
  document.body.appendChild(overlay);
  return overlay;
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function openAboutModal() {
  openModal(
    "About Jury",
    `
    <p class="about-lead">
      Jury is an AI-powered content moderation tool. You define <strong>policies</strong>
      made up of custom <strong>rules</strong>, submit content for review, and an AI model
      returns a structured verdict for every rule — automatically, every time.
    </p>

    <div class="about-steps">
      <div class="about-step">
        <span class="about-step-num">1</span>
        <div>
          <strong>Create a policy</strong>
          <p>A named container for the guidelines you want to enforce.</p>
        </div>
      </div>
      <div class="about-step">
        <span class="about-step-num">2</span>
        <div>
          <strong>Add rules</strong>
          <p>Plain-language descriptions of what's prohibited or required. Jury checks every piece of content against each one.</p>
        </div>
      </div>
      <div class="about-step">
        <span class="about-step-num">3</span>
        <div>
          <strong>Submit content, get verdicts</strong>
          <p>Each rule comes back as no violation, possible violation, or clear violation — color-coded so you can scan results at a glance.</p>
        </div>
      </div>
    </div>

    <p class="about-footer-note">© Built by Mohamed Farouk</p>
    `,
    "about-modal"
  );
}

export function openApiModal() {
  const bodyHtml = `
    <p class="about-lead">Create API keys to access Jury programmatically. Each key is shown in full only once, right after you create it — store it somewhere safe.</p>
    <div id="api-key-created-box"></div>
    <div class="api-key-create-row">
      <input type="text" id="api-key-name-input" placeholder="Key name (optional)" maxlength="100" />
      <button class="btn btn-sm btn-primary" id="create-api-key-btn">+ Create key</button>
    </div>
    <p id="api-key-error" class="form-error hidden"></p>
    <ul class="api-keys-list" id="api-keys-list">
      <li class="empty-hint">Loading keys…</li>
    </ul>
  `;

  const overlay = openModal("API Keys", bodyHtml, "api-modal");
  const content = overlay.querySelector(".modal-content");
  const listEl = content.querySelector("#api-keys-list");
  const errEl = content.querySelector("#api-key-error");
  const createdBox = content.querySelector("#api-key-created-box");
  const nameInput = content.querySelector("#api-key-name-input");
  const createBtn = content.querySelector("#create-api-key-btn");

  function showError(msg) {
    errEl.textContent = msg;
    errEl.classList.remove("hidden");
  }

  function clearError() {
    errEl.classList.add("hidden");
    errEl.textContent = "";
  }

  function renderKeys(keys) {
    if (keys.length === 0) {
      listEl.innerHTML = `<li class="empty-hint">No API keys yet.</li>`;
      return;
    }
    listEl.innerHTML = keys
      .map((k) => {
        const created = new Date(k.created_at).toLocaleDateString();
        const lastUsed = k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never used";
        return `
        <li class="api-key-item ${k.revoked ? "revoked" : ""}" data-id="${k.id}">
          <div class="api-key-info">
            <strong>${escapeHtml(k.name || "Unnamed key")}</strong>
            <code class="api-key-prefix">${escapeHtml(k.prefix)}••••••••</code>
            <span class="api-key-meta">Created ${created} · ${k.revoked ? "Revoked" : lastUsed}</span>
          </div>
          ${!k.revoked ? `<button class="btn-icon revoke-api-key-btn" data-id="${k.id}" title="Revoke key">🗑</button>` : ""}
        </li>`;
      })
      .join("");

    listEl.querySelectorAll(".revoke-api-key-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.id);
        if (!confirm("Revoke this API key? Anything using it will stop working immediately.")) return;
        clearError();
        try {
          await revokeApiKey(id);
          await loadKeys();
        } catch (err) {
          showError(err.message);
        }
      });
    });
  }

  async function loadKeys() {
    try {
      const keys = await fetchApiKeys();
      renderKeys(keys);
    } catch (err) {
      listEl.innerHTML = `<li class="empty-hint">Failed to load keys.</li>`;
      showError(err.message);
    }
  }

  createBtn.addEventListener("click", async () => {
    clearError();
    createBtn.disabled = true;
    try {
      const name = nameInput.value.trim();
      const created = await createApiKey(name);
      nameInput.value = "";
      createdBox.innerHTML = `
        <div class="api-key-created-box">
          <strong>⚠ Copy this key now — it won't be shown again</strong>
          <div class="api-key-secret-row">
            <code class="api-key-secret">${escapeHtml(created.key)}</code>
            <button class="btn btn-sm btn-outline" id="copy-api-key-btn">Copy</button>
          </div>
        </div>`;
      const copyBtn = createdBox.querySelector("#copy-api-key-btn");
      copyBtn.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(created.key);
          copyBtn.textContent = "Copied!";
          setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
        } catch {
          // Clipboard API can fail (e.g. insecure context) — the key is
          // still visible on screen for manual copying.
        }
      });
      await loadKeys();
    } catch (err) {
      showError(err.message);
    } finally {
      createBtn.disabled = false;
    }
  });

  loadKeys();
}

export function openContactModal() {
  const links = [
    { label: "Email", icon: ICONS.email, href: "mailto:mohamedfarouk1994@gmail.com" },
    { label: "Portfolio", icon: ICONS.portfolio, href: "https://mohamedfarouk94.github.io/" },
    { label: "GitHub", icon: ICONS.github, href: "https://github.com/MohamedFarouk94" },
    { label: "LinkedIn", icon: ICONS.linkedin, href: "https://www.linkedin.com/in/mohfarouk94/" },
    { label: "X", icon: ICONS.x, href: "https://x.com/mohfarouk94" },
    { label: "Instagram", icon: ICONS.instagram, href: "https://www.instagram.com/mohfarouk94/" },
  ];

  const rows = links
    .map(
      (l) => `
      <a class="contact-icon-link" href="${l.href}" target="_blank" rel="noopener noreferrer" title="${l.label}" aria-label="${l.label}">
        ${l.icon}
      </a>`
    )
    .join("");

  openModal(
    "Get in touch",
    `
    <p class="about-lead">Hi! My name is Mohamed Farouk. I'm an AI engineer, NLP specialist, and CS researcher.<br>For business, questions, or even general discussion, reach out anywhere below.</p>
    <div class="contact-row">${rows}</div>
    <p class="about-footer-note">Don't hesitate to contact me!</p>
    `,
    "contact-modal"
  );
}

/**
 * Renders a small "API · About · Contact" footer into the given container.
 * Pass { showApi: false } to omit the API tab — used on the logged-out
 * auth page, since key management requires an authenticated user.
 */
export function renderInfoFooter(container, { showApi = true } = {}) {
  container.innerHTML = `
    ${showApi ? `<button class="info-link" id="api-link" type="button">API</button><span class="info-sep">·</span>` : ""}
    <button class="info-link" id="about-link" type="button">About</button>
    <span class="info-sep">·</span>
    <button class="info-link" id="contact-link" type="button">Contact</button>
  `;
  if (showApi) {
    container.querySelector("#api-link").addEventListener("click", openApiModal);
  }
  container.querySelector("#about-link").addEventListener("click", openAboutModal);
  container.querySelector("#contact-link").addEventListener("click", openContactModal);
}