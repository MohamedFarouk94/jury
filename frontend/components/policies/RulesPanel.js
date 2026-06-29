import { addRule, editRule, deleteRule } from "../../services/api.js";

export function renderRulesPanel(container, policy, onRulesChanged = () => {}) {
  let rules = [...(policy.rules || [])];

  function render() {
    container.innerHTML = `
      <div class="rules-header">
        <h3>Rules</h3>
        <button class="btn btn-sm btn-outline" id="add-rule-btn">+ Add rule</button>
      </div>

      <div id="rule-form" class="rule-form hidden">
        <input type="text" id="rule-name-input" placeholder="Rule name" maxlength="100" />
        <textarea id="rule-desc-input" placeholder="Describe what this rule prohibits or requires..." rows="3"></textarea>
        <div class="form-row">
          <button class="btn btn-sm btn-primary" id="save-rule-btn">Save</button>
          <button class="btn btn-sm btn-ghost" id="cancel-rule-btn">Cancel</button>
        </div>
        <p id="rule-form-error" class="form-error hidden"></p>
        <input type="hidden" id="editing-rule-id" value="" />
      </div>

      <ul class="rules-list" id="rules-list">
        ${
          rules.length === 0
            ? `<li class="empty-hint">No rules yet. Add one above.</li>`
            : rules
                .map((r) => `
          <li class="rule-item" data-id="${r.id}">
            <div class="rule-body">
              <strong>${escapeHtml(r.name)}</strong>
              <p>${escapeHtml(r.description)}</p>
            </div>
            <div class="rule-actions">
              <button class="btn-icon edit-rule-btn" data-id="${r.id}" title="Edit">✏️</button>
              <button class="btn-icon delete-rule-btn" data-id="${r.id}" title="Delete">🗑</button>
            </div>
          </li>`)
                .join("")
        }
      </ul>
    `;

    const form = container.querySelector("#rule-form");
    const nameInput = container.querySelector("#rule-name-input");
    const descInput = container.querySelector("#rule-desc-input");
    const editingId = container.querySelector("#editing-rule-id");
    const errEl = container.querySelector("#rule-form-error");

    function openForm(rule = null) {
      form.classList.remove("hidden");
      nameInput.value = rule ? rule.name : "";
      descInput.value = rule ? rule.description : "";
      editingId.value = rule ? rule.id : "";
      errEl.classList.add("hidden");
      nameInput.focus();
    }

    container.querySelector("#add-rule-btn").addEventListener("click", () => openForm());
    container.querySelector("#cancel-rule-btn").addEventListener("click", () => form.classList.add("hidden"));

    container.querySelector("#save-rule-btn").addEventListener("click", async () => {
      const name = nameInput.value.trim();
      const desc = descInput.value.trim();
      if (!name || !desc) {
        errEl.textContent = "Both name and description are required.";
        errEl.classList.remove("hidden");
        return;
      }
      try {
        const ruleId = editingId.value;
        if (ruleId) {
          const updated = await editRule(policy.id, Number(ruleId), name, desc);
          const idx = rules.findIndex((r) => r.id === Number(ruleId));
          if (idx !== -1) rules[idx] = updated;
        } else {
          const created = await addRule(policy.id, name, desc);
          rules.push(created);
        }
        render();
        onRulesChanged();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove("hidden");
      }
    });

    container.querySelectorAll(".edit-rule-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const rule = rules.find((r) => r.id === Number(btn.dataset.id));
        if (rule) openForm(rule);
      });
    });

    container.querySelectorAll(".delete-rule-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.id);
        if (!confirm("Delete this rule?")) return;
        await deleteRule(policy.id, id);
        rules = rules.filter((r) => r.id !== id);
        // Re-sequence local policy_rule_index to stay in sync with backend
        rules.forEach((r, i) => { r.policy_rule_index = i + 1; });
        render();
        onRulesChanged();
      });
    });
  }

  render();

  // Return a live getter for current rules
  return () => rules;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
