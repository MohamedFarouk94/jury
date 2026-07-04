const BASE_URL = window.JURY_API_URL;

function getToken() {
  return localStorage.getItem("jury_token");
}

// FastAPI error bodies aren't always a plain string — pydantic validation
// errors send `detail` as an array of {loc, msg, type} objects, and some
// custom errors send a single object. Turn any of these into a readable
// string instead of letting them stringify to "[object Object]".
function extractErrorMessage(err) {
  const detail = err?.detail;
  if (!detail) return "Request failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === "string" ? d : d.msg || JSON.stringify(d)))
      .join(" ");
  }
  if (typeof detail === "object") return detail.msg || JSON.stringify(detail);
  return "Request failed";
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  //if (!res.ok) {
  //  const err = await res.json().catch(() => ({ detail: "Unknown error" }));
  //  throw new Error(err.detail || "Request failed");
  //}
  if (!res.ok) {
  if (res.status === 401) {
    localStorage.removeItem("jury_token");
    localStorage.removeItem("jury_username");
    window.location.reload();
  }
  const err = await res.json().catch(() => ({ detail: "Unknown error" }));
  throw new Error(extractErrorMessage(err));
}

  if (res.status === 204) return null;
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function signup(username, email, password) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export async function login(username, password) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem("jury_token", data.access_token);
  // We already know the username that was used to authenticate — store it
  // so the UI can display "@username" without needing a separate /me call.
  localStorage.setItem("jury_username", username);
  return data;
}

export function getCurrentUsername() {
  return localStorage.getItem("jury_username");
}

export function logout() {
  localStorage.removeItem("jury_token");
  localStorage.removeItem("jury_username");
}

// ── Policies ─────────────────────────────────────────────────────────────────

export async function fetchPolicies() {
  return request("/policies/");
}

export async function fetchPolicy(id) {
  return request(`/policies/${id}`);
}

export async function createPolicy(name, description) {
  return request("/policies/", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

export async function deletePolicy(id) {
  return request(`/policies/${id}`, { method: "DELETE" });
}

// ── Rules ─────────────────────────────────────────────────────────────────────

export async function addRule(policyId, name, description) {
  return request(`/policies/${policyId}/rules/`, {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });
}

export async function editRule(policyId, ruleId, name, description) {
  return request(`/policies/${policyId}/rules/${ruleId}`, {
    method: "PUT",
    body: JSON.stringify({ name, description }),
  });
}

export async function deleteRule(policyId, ruleId) {
  return request(`/policies/${policyId}/rules/${ruleId}`, { method: "DELETE" });
}

// ── Contents ──────────────────────────────────────────────────────────────────

export async function sendContent(policyId, text) {
  return request("/contents/", {
    method: "POST",
    body: JSON.stringify({ policy_id: policyId, text }),
  });
}

export async function fetchContents(policyId) {
  return request(`/contents/policy/${policyId}`);
}

export async function fetchContent(contentId) {
  return request(`/contents/${contentId}`);
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export async function fetchApiKeys() {
  return request("/api-keys/");
}

export async function createApiKey(name) {
  return request("/api-keys/", {
    method: "POST",
    body: JSON.stringify({ name: name || null }),
  });
}

export async function revokeApiKey(id) {
  return request(`/api-keys/${id}`, { method: "DELETE" });
}