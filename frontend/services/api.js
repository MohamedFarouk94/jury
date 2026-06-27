const BASE_URL = "http://localhost:7860";

function getToken() {
  return localStorage.getItem("jury_token");
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
    window.location.reload();
  }
  const err = await res.json().catch(() => ({ detail: "Unknown error" }));
  throw new Error(err.detail || "Request failed");
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
  return data;
}

export function logout() {
  localStorage.removeItem("jury_token");
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
