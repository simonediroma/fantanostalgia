// Listone (players) upload + assignment API calls

async function apiUploadListone(leagueId, file, force = false) {
  const fd = new FormData();
  fd.append('file', file);
  const q = force ? '?force=true' : '';
  return apiFetch(`/admin/league/${leagueId}/listone${q}`, { method: 'POST', body: fd });
}

async function apiListPlayers(leagueId) {
  return apiFetch(`/league/${leagueId}/players`);
}

async function apiAssignPlayers(leagueId, assignments) {
  return jsonPost(`/admin/league/${leagueId}/assign`, assignments);
}
