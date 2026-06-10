// Mapping alter ego API calls

async function apiGenerateMapping(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/mapping/generate`, { method: 'POST' });
}

async function apiRevealMapping(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/mapping/reveal`, { method: 'POST' });
}

async function apiGetAdminMapping(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/mapping`);
}

async function apiGetPublicMapping(leagueId) {
  return apiFetch(`/league/${leagueId}/mapping`);
}
