// Collegamento Leghe Fantacalcio (pannello globale) — API calls

// Fetch diretta, non apiFetch: per l'admin da variabili d'ambiente (senza
// utente) questa chiamata risponde 401, che non deve causare il logout.
async function apiFantacalcioLink() {
  const res = await fetch('/auth/user/fantacalcio', { credentials: 'include' });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function apiFantacalcioExplore(league, path) {
  const qs = new URLSearchParams({ league, path });
  return apiFetch(`/admin/fantacalcio/explore?${qs}`);
}
