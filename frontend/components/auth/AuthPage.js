import { login, signup } from "../../services/api.js";
import { renderInfoFooter } from "../shared/InfoModals.js";

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
          <input type="password" name="password" placeholder="••••••••" required />
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
          <input type="password" name="password" placeholder="••••••••" required minlength="8" />
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

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();
    const fd = new FormData(loginForm);
    try {
      await login(fd.get("username"), fd.get("password"));
      onSuccess();
    } catch (err) {
      showError(err.message);
    }
  });

  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearError();
    const fd = new FormData(signupForm);
    try {
      await signup(fd.get("username"), fd.get("email"), fd.get("password"));
      await login(fd.get("username"), fd.get("password"));
      onSuccess();
    } catch (err) {
      showError(err.message);
    }
  });
}