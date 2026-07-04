import { logout, fetchPolicy, getCurrentUsername } from "../services/api.js";
import { renderPoliciesSidebar } from "../components/policies/PoliciesSidebar.js";
import { renderRulesPanel } from "../components/policies/RulesPanel.js";
import { renderContentFeed } from "../components/content/ContentFeed.js";
import { renderInfoFooter } from "../components/shared/InfoModals.js";

export async function renderDashboard(onLogout) {
  const app = document.getElementById("app");
  const username = getCurrentUsername();

  app.innerHTML = `
    <div class="dashboard">
      <header class="topbar">
        <button class="mobile-toggle" id="sidebar-toggle" aria-label="Toggle policies">☰</button>
        <div class="topbar-brand">
          <img src="assets/logo.jpg" alt="Jury logo" class="logo-img" />
          <span class="brand-name">Jury</span>
          ${username ? `<span class="username-badge" title="Logged in as ${username}">@${username}</span>` : ""}
        </div>
        <div class="topbar-right">
          <div class="info-footer info-footer-inline" id="topbar-info-footer"></div>
          <button class="btn btn-ghost btn-sm" id="logout-btn">Log out</button>
        </div>
      </header>
      <div class="dashboard-body">
        <div class="panel-backdrop" id="panel-backdrop"></div>
        <aside class="sidebar" id="sidebar"></aside>
        <main class="main-area" id="main-area">
          <div class="empty-state">
            <div class="empty-icon">📋</div>
            <p>Select or create a policy to get started.</p>
          </div>
        </main>
        <aside class="rules-panel" id="rules-panel">
          <div class="empty-state small">
            <p>Select a policy to see its rules.</p>
          </div>
        </aside>
      </div>
    </div>`;

  document.getElementById("logout-btn").addEventListener("click", () => {
    logout();
    onLogout();
  });

  renderInfoFooter(document.getElementById("topbar-info-footer"));

  // ── Mobile drawer toggles ──────────────────────────────────────────────────
  // The Policies drawer still has its own topbar button (☰). The Rules drawer
  // has no topbar button anymore — it's opened contextually from underneath
  // whichever policy is currently selected, inside the sidebar itself.
  const sidebarEl = document.getElementById("sidebar");
  const rulesPanelEl = document.getElementById("rules-panel");
  const backdrop = document.getElementById("panel-backdrop");
  const sidebarToggleBtn = document.getElementById("sidebar-toggle");

  function closePanels() {
    sidebarEl.classList.remove("open");
    rulesPanelEl.classList.remove("open");
    backdrop.classList.remove("visible");
  }

  function openRulesPanel() {
    closePanels();
    rulesPanelEl.classList.add("open");
    backdrop.classList.add("visible");
  }

  sidebarToggleBtn.addEventListener("click", () => {
    const willOpen = !sidebarEl.classList.contains("open");
    closePanels();
    if (willOpen) {
      sidebarEl.classList.add("open");
      backdrop.classList.add("visible");
    }
  });

  backdrop.addEventListener("click", closePanels);

  // PoliciesSidebar dispatches this when the user taps the "Rules" link
  // nested under the currently-selected policy (mobile only).
  window.addEventListener("jury:open-rules", openRulesPanel);

  let feedHandle = null;

  async function onSelectPolicy(policyId) {
    const mainArea = document.getElementById("main-area");
    const rulesPanel = document.getElementById("rules-panel");

    closePanels(); // auto-close drawers on mobile once a policy is picked

    if (feedHandle) { feedHandle.cleanup(); feedHandle = null; }

    if (!policyId) {
      mainArea.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>Select or create a policy to get started.</p></div>`;
      rulesPanel.innerHTML = `<div class="empty-state small"><p>Select a policy to see its rules.</p></div>`;
      return;
    }

    mainArea.innerHTML = `<div class="loading">Loading…</div>`;
    rulesPanel.innerHTML = `<div class="loading">Loading…</div>`;

    try {
      const policy = await fetchPolicy(policyId);

      // 1. Render rules panel FIRST — this returns the live getRules getter
      const getRules = renderRulesPanel(rulesPanel, policy, () => {
        feedHandle?.onRulesChanged();
      });

      // 2. Render content feed with the now-populated getRules
      feedHandle = await renderContentFeed(mainArea, policy, getRules);
    } catch (err) {
      mainArea.innerHTML = `<div class="error-state">Failed to load policy: ${err.message}</div>`;
    }
  }

  await renderPoliciesSidebar(document.getElementById("sidebar"), onSelectPolicy);
}