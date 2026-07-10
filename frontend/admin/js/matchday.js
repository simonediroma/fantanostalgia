// Matchday (formazioni, sorteggio, punteggi) API calls

async function apiUploadFormazioni(leagueId, matchday, file) {
  const fd = new FormData();
  fd.append('file', file);
  return apiFetch(`/admin/league/${leagueId}/lineups/${matchday}`, { method: 'POST', body: fd });
}

async function apiDrawMatchday(leagueId, matchday) {
  return apiFetch(`/admin/league/${leagueId}/draw/${matchday}`, { method: 'POST' });
}

async function apiCalculateScores(leagueId, matchday) {
  return apiFetch(`/admin/league/${leagueId}/scores/${matchday}`, { method: 'POST' });
}

async function apiListDraws(leagueId) {
  return apiFetch(`/league/${leagueId}/draws`);
}

async function apiListMatchdays(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/matchdays`);
}

async function apiGetScores(leagueId, matchday) {
  return apiFetch(`/league/${leagueId}/scores/${matchday}`);
}

// ── Gran Premi ────────────────────────────────────────────────────────────────

async function apiListFreeHistoric(leagueId, role) {
  const q = role ? `?role=${encodeURIComponent(role)}` : '';
  return apiFetch(`/admin/league/${leagueId}/granpremio/free-players${q}`);
}

async function apiCreateGranPremio(leagueId, body) {
  return jsonPost(`/admin/league/${leagueId}/granpremio`, body);
}

async function apiResolveGranPremio(leagueId, gpId) {
  return apiFetch(`/admin/league/${leagueId}/granpremio/${gpId}/resolve`, { method: 'POST' });
}

async function apiListGranPremi(leagueId) {
  return apiFetch(`/league/${leagueId}/granpremio`);
}
