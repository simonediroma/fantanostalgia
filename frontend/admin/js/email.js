// Diagnostica email (pannello globale) — API calls

async function apiEmailStatus() {
  return apiFetch('/admin/email/status');
}

async function apiEmailTest(to) {
  return jsonPost('/admin/email/test', { to });
}

async function apiProcessEmailQueue() {
  return apiFetch('/admin/process-email-queue', { method: 'POST' });
}
