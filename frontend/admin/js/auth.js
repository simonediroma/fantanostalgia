// Session management — cookie-based via /auth endpoints

async function doLogin(username, password) {
  return jsonPost('/auth/login', { username, password });
}

async function doLogout() {
  try { await apiFetch('/auth/logout', { method: 'POST' }); } catch {}
  sessionStorage.removeItem('fn_user');
}

async function checkSession() {
  try {
    const d = await apiFetch('/auth/me');
    if (d && d.username) {
      sessionStorage.setItem('fn_user', d.username);
      return d.username;
    }
  } catch {}
  return null;
}
