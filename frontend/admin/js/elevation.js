// Elevazione coach → admin — API calls

async function apiListElevationRequests() {
  return apiFetch('/auth/admin/elevation-requests');
}

async function apiApproveElevationRequest(id) {
  return apiFetch(`/auth/admin/elevation-requests/${id}/approve`, { method: 'POST' });
}

async function apiRejectElevationRequest(id) {
  return apiFetch(`/auth/admin/elevation-requests/${id}/reject`, { method: 'POST' });
}
