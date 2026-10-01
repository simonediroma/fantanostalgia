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

async function apiFantacalcioCompetitions(league) {
  return apiFetch(`/admin/fantacalcio/${encodeURIComponent(league)}/competitions`);
}

async function apiFantacalcioCalendar(league, competitionId) {
  return apiFetch(`/admin/fantacalcio/${encodeURIComponent(league)}/calendar/${competitionId}`);
}

async function apiImportLineupsFromFantacalcio(leagueId, matchday, body) {
  return jsonPost(`/admin/league/${leagueId}/lineups/${matchday}/fantacalcio`, body);
}

async function apiSyncRostersFromFantacalcio(leagueId, body) {
  return jsonPost(`/admin/league/${leagueId}/rosters/fantacalcio`, body);
}
