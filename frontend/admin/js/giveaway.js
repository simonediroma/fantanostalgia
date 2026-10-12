// Assegnazione giornata — API calls

async function apiGiveawayRules() {
  return apiFetch('/admin/giveaway/rules');
}

async function apiSaveGiveawayRules(rules) {
  return jsonPut('/admin/giveaway/rules', rules);
}

async function apiGiveawayPreview(leagueId, matchday) {
  return apiFetch(`/admin/league/${leagueId}/giveaway/${matchday}`);
}

async function apiRunGiveaway(leagueId, matchday) {
  return jsonPost(`/admin/league/${leagueId}/giveaway/${matchday}`, {});
}
