import { fetchPolicies, createPolicy, deletePolicy } from "../../services/api.js";

export async function renderPoliciesSidebar(container, onSelectPolicy) {
  let policies = await fetchPolicies();

  function render() {
    container.innerHTML = `
      <div class="sidebar-header">
        <h2>Policies</h2>
        <button class="btn btn-sm btn-outline" id="new-policy-btn">+ New</button>
      </div>
      <ul class="policy-list" id="policy-list">
        ${
          policies.length === 0
            ? `<li class="empty-hint">No policies yet.</li>`
            : policies
                .map(
                  (p) => `
          <li class="policy-item" data-id="${p.id}">
            <span class="policy-name">${escapeHtml(p.name)}</span>
            <button class="btn-icon delete-policy-btn" data-id="${p.id}" title="Delete policy">🗑</button>
          </li>`
                )
                .join("")
        }
      </ul>

      <div id="new-policy-form" class="new-policy-form hidden">
        <input type="text" id="policy-name-input" placeholder="Policy name" maxlength="100" />
        <textarea id="policy-desc-input" placeholder="Description (optional)" rows="2"></textarea>
        <div class="form-row">
          <button class="btn btn-sm btn-primary" id="save-policy-btn">Save</button>
          <button class="btn btn-sm btn-ghost" id="cancel-policy-btn">Cancel</button>
        </div>
        <p id="policy-form-error" class="form-error hidden"></p>
      </div>
    `;

    container.querySelector("#new-policy-btn").addEventListener("click", () => {
      container.querySelector("#new-policy-form").classList.toggle("hidden");
    });

    container.querySelector("#cancel-policy-btn").addEventListener("click", () => {
      container.querySelector("#new-policy-form").classList.add("hidden");
    });

    container.querySelector("#save-policy-btn").addEventListener("click", async () => {
      const name = container.querySelector("#policy-name-input").value.trim();
      const desc = container.querySelector("#policy-desc-input").value.trim();
      const errEl = container.querySelector("#policy-form-error");
      if (!name) {
        errEl.textContent = "Name is required.";
        errEl.classList.remove("hidden");
        return;
      }
      try {
        const policy = await createPolicy(name, desc || null);
        policies.push(policy);
        render();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove("hidden");
      }
    });

    container.querySelectorAll(".policy-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        if (e.target.closest(".delete-policy-btn")) return;
        container.querySelectorAll(".policy-item").forEach((el) => el.classList.remove("active"));
        item.classList.add("active");
        onSelectPolicy(Number(item.dataset.id));
      });
    });

    container.querySelectorAll(".delete-policy-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = Number(btn.dataset.id);
        if (!confirm("Delete this policy and all its rules and content?")) return;
        await deletePolicy(id);
        policies = policies.filter((p) => p.id !== id);
        render();
        onSelectPolicy(null);
      });
    });
  }

  render();
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
