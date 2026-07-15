// Gestione utenti (pannello globale) — API calls

async function apiListUsers() {
  return apiFetch('/auth/admin/users');
}

async function apiAdminResetPassword(userId, newPassword) {
  return jsonPost(`/auth/admin/users/${userId}/reset-password`, { new_password: newPassword });
}
