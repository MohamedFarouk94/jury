import { logout, fetchPolicy } from "../services/api.js";
import { renderPoliciesSidebar } from "../components/policies/PoliciesSidebar.js";
import { renderRulesPanel } from "../components/policies/RulesPanel.js";
import { renderContentFeed } from "../components/content/ContentFeed.js";

export async function renderDashboard(onLogout) {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="dashboard">
      <header class="topbar">
        <div class="topbar-brand">
          <span class="logo-icon">⚖️</span>
          <span class="brand-name">Jury</span>
        </div>
        <button class="btn btn-ghost btn-sm" id="logout-btn">Log out</button>
      </header>
      <div class="dashboard-body">
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

  let feedHandle = null;

  async function onSelectPolicy(policyId) {
    const mainArea = document.getElementById("main-area");
    const rulesPanel = document.getElementById("rules-panel");

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
