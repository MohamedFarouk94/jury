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

      // Render content feed first to get onRulesChanged callback
      feedHandle = await renderContentFeed(mainArea, policy, getRules);

      // Render rules panel, passing onRulesChanged so the feed button updates
      renderRulesPanel(rulesPanel, policy, feedHandle.onRulesChanged);
    } catch (err) {
      mainArea.innerHTML = `<div class="error-state">Failed to load policy: ${err.message}</div>`;
    }
  }

  // getRules is set by renderRulesPanel; placeholder until then
  let getRules = () => [];

  // Wrap renderRulesPanel to capture its getRules return
  const origRenderRulesPanel = renderRulesPanel;
  const _renderRulesPanel = (container, policy, onRulesChanged) => {
    getRules = origRenderRulesPanel(container, policy, onRulesChanged);
  };

  // Patch onSelectPolicy to use the wrapper
  async function onSelectPolicyPatched(policyId) {
    const mainArea = document.getElementById("main-area");
    const rulesPanel = document.getElementById("rules-panel");

    if (feedHandle) { feedHandle.cleanup(); feedHandle = null; }
    getRules = () => [];

    if (!policyId) {
      mainArea.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>Select or create a policy to get started.</p></div>`;
      rulesPanel.innerHTML = `<div class="empty-state small"><p>Select a policy to see its rules.</p></div>`;
      return;
    }

    mainArea.innerHTML = `<div class="loading">Loading…</div>`;
    rulesPanel.innerHTML = `<div class="loading">Loading…</div>`;

    try {
      const policy = await fetchPolicy(policyId);

      // Render feed with a getter that always reads current getRules
      feedHandle = await renderContentFeed(mainArea, policy, () => getRules());

      // Render rules panel; its return value is the live rules getter
      getRules = renderRulesPanel(rulesPanel, policy, feedHandle.onRulesChanged);
    } catch (err) {
      mainArea.innerHTML = `<div class="error-state">Failed to load policy: ${err.message}</div>`;
    }
  }

  await renderPoliciesSidebar(document.getElementById("sidebar"), onSelectPolicyPatched);
}
