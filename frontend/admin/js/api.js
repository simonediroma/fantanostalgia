// Generic fetch wrapper — cookie-based auth, 401 → login redirect
const BASE = '';

async function apiFetch(path, opts = {}) {
  const res = await fetch(BASE + path, { credentials: 'include', ...opts });
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('json') ? await res.json().catch(() => ({})) : {};
  if (!res.ok) {
    if (res.status === 401 && path !== '/auth/me') {
      sessionStorage.removeItem('fn_user');
      showLoginPage();
    }
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

function jsonPost(path, body) {
  return apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function jsonPut(path, body) {
  return apiFetch(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
