// Foto giocatori storici (Wikidata) — API calls

async function apiFetchHistoricPhotos() {
  return jsonPost('/admin/historic/photos/fetch', {});
}

async function apiSetHistoricPhoto(playerId, photoUrl, photoCredit) {
  return jsonPut(`/admin/historic/players/${playerId}/photo`, {
    photo_url: photoUrl, photo_credit: photoCredit,
  });
}
