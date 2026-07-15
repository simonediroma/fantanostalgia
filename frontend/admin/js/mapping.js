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

// Nuovi endpoint: pool nostalgia + gestione allenatori
async function apiAssignPools(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/mapping/assign-pools`, { method: 'POST' });
}

async function apiCoachesStatus(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/coaches-status`);
}

async function apiCloseAssociations(leagueId) {
  return apiFetch(`/admin/league/${leagueId}/mapping/close-associations`, { method: 'POST' });
}

async function apiCreateInvite(leagueId, managerId) {
  return apiFetch(`/admin/league/${leagueId}/managers/${managerId}/invite`, { method: 'POST' });
}

async function apiResetPassword(leagueId, managerId, newPassword) {
  return jsonPost(`/admin/league/${leagueId}/managers/${managerId}/reset-password`, {
    new_password: newPassword,
  });
}
