import { login, signup } from "../../services/api.js";
import { renderInfoFooter } from "../shared/InfoModals.js";

const EYE_OPEN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>`;
const EYE_CLOSED = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 5.2A11.6 11.6 0 0 1 12 5c7 0 11 7 11 7a18 18 0 0 1-3.4 4.3M6.6 6.6A18 18 0 0 0 1 12s4 7 11 7a10.9 10.9 0 0 0 5.4-1.4"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>`;

export function renderAuthPage(onSuccess) {
  const app = document.getElementById("app");
  app.innerHTML = "";

  const container = document.createElement("div");
  container.className = "auth-container";

  container.innerHTML = `
    <div class="auth-box">
      <div class="auth-logo">
        <span class="logo-icon">⚖️</span>
        <h1>Jury</h1>
        <p class="auth-tagline">AI-powered content moderation</p>
        <p class="auth-blurb">Set up rules, submit content, and get instant AI-reviewed verdicts.</p>
      </div>

      <div class="auth-tabs">
        <button class="tab-btn active" data-tab="login">Log in</button>
        <button class="tab-btn" data-tab="signup">Sign up</button>
      </div>

      <div id="auth-error" class="auth-error hidden"></div>

      <form id="login-form" class="auth-form">
        <label>Username
          <input type="text" name="username" placeholder="your_handle" required />
        </label>
        <label>Password
          <div class="password-field">
            <input type="password" name="password" placeholder="••••••••" required />
            <button type="button" class="eye-toggle" aria-label="Show password">${EYE_OPEN}</button>
          </div>
        </label>
        <button type="submit" class="btn btn-primary btn-full">Log in</button>
      </form>

      <form id="signup-form" class="auth-form hidden">
        <label>Username
          <input type="text" name="username" placeholder="your_handle" required />
        </label>
        <label>Email
          <input type="email" name="email" placeholder="you@example.com" required />
        </label>
        <label>Password
          <div class="password-field">
            <input type="password" name="password" id="signup-password" placeholder="••••••••" required minlength="8" />
            <button type="button" class="eye-toggle" aria-label="Show password">${EYE_OPEN}</button>
          </div>
        </label>
        <label>Confirm password
          <div class="password-field">
            <input type="password" name="confirmPassword" id="signup-confirm-password" placeholder="••••••••" required minlength="8" />
            <button type="button" class="eye-toggle" aria-label="Show password">${EYE_OPEN}</button>
          </div>
          <p id="password-match-hint" class="form-hint hidden"></p>
        </label>
        <button type="submit" class="btn btn-primary btn-full">Create account</button>
      </form>

      <div class="info-footer" id="info-footer"></div>
    </div>
  `;

  app.appendChild(container);
  renderInfoFooter(container.querySelector("#info-footer"));

  const tabs = container.querySelectorAll(".tab-btn");
  const loginForm = container.querySelector("#login-form");
  const signupForm = container.querySelector("#signup-form");
  const errorBox = container.querySelector("#auth-error");

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function clearError() {
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const which = tab.dataset.tab;
      loginForm.classList.toggle("hidden", which !== "login");
      signupForm.classList.toggle("hidden", which !== "signup");
      clearError();
    });
  });

  // ── Show/hide password toggles ────────────────────────────────────────────
  container.querySelectorAll(".eye-toggle").forEach((btn) => {
    const input = btn.previousElementSibling;
    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.innerHTML = showing ? EYE_OPEN : EYE_CLOSED;
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  // ── Live password-match indicator (signup only) ───────────────────────────
  const signupPassword = container.querySelector("#signup-password");
  const signupConfirm = container.querySelector("#signup-confirm-password");
  const matchHint = container.querySelector("#password-match-hint");

  function updateMatchHint() {
    const pw = signupPassword.value;
    const confirm = signupConfirm.value;
    if (!confirm) {
      matchHint.classList.add("hidden");
      return;
    }
    matchHint.classList.remove("hidden");
    if (pw === confirm) {
      matchHint.textContent = "Passwords match ✓";
      matchHint.classList.remove("hint-error");
      matchHint.classList.add("hint-success");
    } else {
      matchHint.textContent = "Passwords do not match ✗";
      matchHint.classList.remove("hint-success");
      matchHint.classList.add("hint-error");
    }
  }

  signupPassword.addEventListener("input", updateMatchHint);
  signupConfirm.addEventListener("input", updateMatchHint);

  // ── Submit handlers ────────────────────────────────────────────────────────
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();
    const fd = new FormData(loginForm);
    // Trim identifiers (not the password itself) to avoid stray whitespace
    // from mobile keyboards / copy-paste causing spurious login failures.
    const username = fd.get("username").trim();
    const password = fd.get("password");
    try {
      await login(username, password);
      onSuccess();
    } catch (err) {
      showError(err.message);
    }
  });

  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();
    const fd = new FormData(signupForm);
    const username = fd.get("username").trim();
    const email = fd.get("email").trim();
    const password = fd.get("password");
    const confirmPassword = fd.get("confirmPassword");
    if (password !== confirmPassword) {
      showError("Passwords do not match.");
      return;
    }
    try {
      await signup(username, email, password);
      await login(username, password);
      onSuccess();
    } catch (err) {
      showError(err.message);
    }
  });
}