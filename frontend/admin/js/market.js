// Mercato dei giocatori storici — API calls

async function apiListMarketFreePlayers(leagueId, role) {
  const q = role ? `?role=${encodeURIComponent(role)}` : '';
  return apiFetch(`/admin/league/${leagueId}/market/free-players${q}`);
}

async function apiCreateMarket(leagueId, body) {
  return jsonPost(`/admin/league/${leagueId}/market`, body);
}

async function apiGetCurrentMarket(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/market/current`);
}

async function apiCloseMarketCuts(leagueId, marketId) {
  return apiFetch(`/admin/league/${leagueId}/market/${marketId}/close-cuts`, { method: 'POST' });
}

async function apiResolveMarket(leagueId, marketId) {
  return apiFetch(`/admin/league/${leagueId}/market/${marketId}/resolve`, { method: 'POST' });
}
