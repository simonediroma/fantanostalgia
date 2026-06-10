// League + Manager API calls

async function apiListLeagues() {
  return apiFetch('/league');
}

async function apiGetLeague(id) {
  return apiFetch(`/league/${id}`);
}

async function apiCreateLeague(body) {
  return jsonPost('/admin/league', body);
}

async function apiUpdateLeague(id, body) {
  return jsonPut(`/admin/league/${id}`, body);
}

async function apiListManagers(leagueId) {
  return apiFetch(`/league/${leagueId}/managers`);
}

async function apiCreateManager(leagueId, body) {
  return jsonPost(`/admin/league/${leagueId}/managers`, body);
}
