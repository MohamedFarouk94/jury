window.JURY_API_URL = window.JURY_API_URL || "http://localhost:8000";
import { renderAuthPage } from "./components/auth/AuthPage.js";
import { renderDashboard } from "./pages/Dashboard.js";

function isLoggedIn() {
  return !!localStorage.getItem("jury_token");
}

function init() {
  if (isLoggedIn()) {
    renderDashboard(onLogout);
  } else {
    renderAuthPage(onLogin);
  }
}

function onLogin() {
  renderDashboard(onLogout);
}

function onLogout() {
  renderAuthPage(onLogin);
}

init();
