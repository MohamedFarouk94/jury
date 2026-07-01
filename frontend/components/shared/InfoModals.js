// Shared About / Contact modals — used from both AuthPage and Dashboard
// so they're reachable whether you're logged in or not.

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
}

export function openAboutModal() {
  openModal(
    "About Jury",
    `
    <p class="about-lead">
      Jury is an AI-powered content moderation tool. You define <strong>policies</strong>
      made up of custom <strong>rules</strong>, submit content for review, and an LLM
      returns a structured verdict for every rule — automatically, every time.
    </p>

    <div class="about-steps">
      <div class="about-step">
        <span class="about-step-num">1</span>
        <div>
          <strong>Create a policy</strong>
          <p>A named container for the guidelines you want to enforce — e.g. "Community Comments" or "Marketplace Listings".</p>
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

    <p class="about-footer-note">Built by Mohamed Farouk</p>
    `,
    "about-modal"
  );
}

export function openContactModal() {
  const links = [
    { label: "", icon: "✉️", href: "mailto:mohamedfarouk1994@gmail.com", text: "Mail<br>" },
    { label: "", icon: "🌐", href: "https://mohamedfarouk94.github.io/", text: "Portfolio<br>" },
    { label: "", icon: "💻", href: "https://github.com/MohamedFarouk94", text: "@MohamedFarouk94<br>" },
    { label: "", icon: "🔗", href: "https://www.linkedin.com/in/mohfarouk94/", text: "/in/mohfarouk94<br>" },
    { label: "", icon: "𝕏", href: "https://x.com/mohfarouk94", text: "@mohfarouk94<br>" },
    { label: "", icon: "📷", href: "https://www.instagram.com/mohfarouk94/", text: "@mohfarouk94<br>" },
  ];

  const rows = links
    .map(
      (l) => `
      <a class="contact-link" href="${l.href}" target="_blank" rel="noopener noreferrer">
        <span class="contact-icon">${l.icon}</span>
        <span class="contact-text">
          <strong>${l.label}</strong>
          <span>${l.text}</span>
        </span>
      </a>`
    )
    .join("");

  openModal(
    "Get in touch",
    `
    <p class="about-lead">Questions, feedback, or bug reports — reach out anywhere below.</p>
    <div class="contact-grid">${rows}</div>
    <p class="about-footer-note">Don't hesitate to contact me.</p>
    `,
    "contact-modal"
  );
}

/**
 * Renders a small "About · Contact" footer into the given container.
 */
export function renderInfoFooter(container) {
  container.innerHTML = `
    <button class="info-link" id="about-link" type="button">About</button>
    <span class="info-sep">·</span>
    <button class="info-link" id="contact-link" type="button">Contact</button>
  `;
  container.querySelector("#about-link").addEventListener("click", openAboutModal);
  container.querySelector("#contact-link").addEventListener("click", openContactModal);
}