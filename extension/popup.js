// FantaNostalgia Admin — popup.
// Le chiamate ad apileague.fantacalcio.it girano dentro la pagina di
// leghe.fantacalcio.it (stessa origine e sessione del sito): il token di lega
// si legge dal localStorage della pagina e non esce mai dalla pagina.
// Al nostro server arrivano solo i dati, autenticati con la chiave estensione.

const $ = (id) => document.getElementById(id);
let settings = {};
let tabId = null;
let calendar = [];

function show(text, isError = false) {
  const el = $('msg');
  el.textContent = text;
  el.className = 'msg' + (isError ? ' error' : '');
  el.hidden = !text;
}

function fillSelect(sel, options, selected) {
  sel.replaceChildren(...options.map(([value, label]) => {
    const o = document.createElement('option');
    o.value = value;
    o.textContent = label;
    o.selected = String(value) === String(selected);
    return o;
  }));
}

async function busy(fn) {
  document.querySelectorAll('button').forEach(b => { b.disabled = true; });
  try {
    await fn();
  } catch (err) {
    show(err.message, true);
  } finally {
    document.querySelectorAll('button').forEach(b => { b.disabled = false; });
  }
}

// ── Pagina Fantacalcio ──────────────────────────────────────────────────────

// Eseguita nella pagina (world MAIN): deve essere autosufficiente.
// requests: [{path, paginate}] — con paginate unisce `data` di tutte le pagine.
async function pageFetch(requests) {
  const APP_KEY = 'ICiELOObd5DF5uJEATi77CRvHiiRuMU0';
  const parse = (v) => { try { return typeof v === 'string' ? JSON.parse(v) : v; } catch { return null; } };
  const alias = location.pathname.split('/')[1];
  const store = parse(localStorage.getItem('LEAGUES2024_LOCAL'));
  if (!store) return { error: 'Sessione Fantacalcio non trovata: accedi a leghe.fantacalcio.it.' };
  let user = parse(store['current-user']);
  if (user === null || typeof user !== 'object') user = parse(store[`current-user-${user}`]);
  const leagues = (user && (user.leagues || user.leghe)) || [];
  const league = leagues.find(l => l.alias === alias);
  if (!league) return { error: 'Apri una pagina della tua lega su leghe.fantacalcio.it.' };
  const token = league.token || league.jwt;
  if (!token) return { error: 'Token di lega non trovato: rifai login su Fantacalcio.' };

  let first = true;
  async function get(path) {
    if (!first) await new Promise(r => setTimeout(r, 500));
    first = false;
    const res = await fetch('https://apileague.fantacalcio.it' + path, {
      headers: { app_key: APP_KEY, Authorization: 'Bearer ' + token, Accept: 'application/json' },
      credentials: 'omit',
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = body && (body.message || body.code) ? `${body.code || ''} ${body.message || ''}` : '';
      const hint = res.status === 401 ? ' (sessione scaduta: rifai login su Fantacalcio)' : '';
      throw new Error(`Fantacalcio ${res.status} ${detail.trim()} su ${path.split('?')[0]}${hint}`);
    }
    return body;
  }

  try {
    const out = [];
    for (const req of requests) {
      if (!req.paginate) { out.push(await get(req.path)); continue; }
      const merged = { data: [], item: null };
      for (let page = 1; ; page++) {
        const sep = req.path.includes('?') ? '&' : '?';
        const body = await get(`${req.path}${sep}page=${page}&pageSize=50`);
        merged.data.push(...(body.data || []));
        merged.item = body.item ?? merged.item;
        if (!body.nextPage) break;
      }
      out.push(merged);
    }
    return { league: { alias, name: league.name }, data: out };
  } catch (err) {
    return { error: err.message };
  }
}

async function fcFetch(requests) {
  const [res] = await chrome.scripting.executeScript({
    target: { tabId }, world: 'MAIN', func: pageFetch, args: [requests],
  });
  const r = res && res.result;
  if (!r) throw new Error('Nessuna risposta dalla pagina di Fantacalcio: ricaricala e riprova.');
  if (r.error) throw new Error(r.error);
  return r;
}

const asList = (body, key = 'data') => (Array.isArray(body) ? body : (body && body[key]) || []);

// ── Server FantaNostalgia ───────────────────────────────────────────────────

async function api(path, body) {
  const res = await fetch(settings.baseUrl + path, {
    method: body ? 'POST' : 'GET',
    headers: { Authorization: 'Bearer ' + settings.apiKey, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || `FantaNostalgia ha risposto ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

function rosterSummary(s) {
  if (!s) return '';
  if (s.error) return `Sync rose non riuscita: ${s.error}`;
  const n = s.added.length + s.moved.length + s.released.length;
  if (!n) return 'Rose già allineate.';
  let msg = `Rose: +${s.added.length} acquisti, ${s.moved.length} spostati, ${s.released.length} svincolati`
    + `\n${[...s.added, ...s.moved, ...s.released].join('\n')}`;
  if (s.realign.length) msg += `\nAlter ego da riassociare per: ${s.realign.join(', ')}`;
  return msg;
}

async function fetchRosterData() {
  const r = await fcFetch([
    { path: '/onboarding/v1/league/players' },
    { path: '/onboarding/v1/league/teams', paginate: true },
  ]);
  const [players, teams] = r.data;
  return { players: asList(players, 'players'), teams: teams.data, total: teams.item };
}

// ── UI ──────────────────────────────────────────────────────────────────────

async function remember(key, value) {
  await chrome.storage.local.set({ [key]: value });
}

async function loadDays() {
  const compId = $('competition').value;
  if (!compId) return;
  const r = await fcFetch([{ path: `/onboarding/v1/league/competition/calendar/${compId}` }]);
  calendar = asList(r.data[0]);
  const days = calendar.filter(d => d.calculated);
  if (!days.length) {
    fillSelect($('day'), [], null);
    $('target').value = '';
    show('Nessuna giornata calcolata in questa competizione.');
    return;
  }
  const last = days[days.length - 1].matchDay;
  fillSelect($('day'), days.map(d => [d.matchDay, `Giornata ${d.matchDay} (${d.championshipMatchDay}ª Serie A)`]), last);
  $('target').value = last;
}

async function loadMain() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || !tab.url.startsWith('https://leghe.fantacalcio.it/')) {
    show('Apri la tua lega su leghe.fantacalcio.it e riapri l\'estensione.', true);
    return;
  }
  tabId = tab.id;
  $('main').hidden = false;

  const leagues = await api('/ext/v1/leagues');
  const r = await fcFetch([{ path: '/onboarding/v1/league/competitions' }]);
  const alias = r.league.alias;
  const prefs = (await chrome.storage.local.get(`prefs_${alias}`))[`prefs_${alias}`] || {};
  fillSelect($('fnLeague'), leagues.map(l => [l.id, l.name]), prefs.fnLeague);
  const comps = asList(r.data[0]);
  fillSelect($('competition'), comps.map(c => [c.id, c.name]), prefs.competition);

  const savePrefs = () => remember(`prefs_${alias}`, { fnLeague: $('fnLeague').value, competition: $('competition').value });
  $('fnLeague').onchange = savePrefs;
  $('competition').onchange = () => busy(async () => { await savePrefs(); show(''); await loadDays(); });
  $('day').onchange = () => { $('target').value = $('day').value; };
  show(`Lega Fantacalcio: ${r.league.name || alias}`);
  await loadDays();
}

$('syncRosters').onclick = () => busy(async () => {
  show('Scarico le rose…');
  const { players, teams, total } = await fetchRosterData();
  const url = `/ext/v1/league/${$('fnLeague').value}/rosters`;
  let res;
  try {
    res = await api(url, { teams, total, players });
  } catch (err) {
    if (err.status !== 409 || !err.message.includes('soglia')) throw err;
    if (!confirm(`${err.message}\n\nProcedere comunque? I giocatori svincolati escono dalle rose.`)) {
      show('Sync annullata.');
      return;
    }
    res = await api(url, { teams, total, players, force: true });
  }
  show(rosterSummary(res));
});

$('importDay').onclick = () => busy(async () => {
  const day = calendar.find(d => String(d.matchDay) === $('day').value);
  const target = parseInt($('target').value, 10);
  if (!day || !target) { show('Scegli la giornata e dove salvarla.', true); return; }
  const compId = $('competition').value;
  show('Scarico rose e formazioni…');
  const r = await fcFetch([
    { path: '/onboarding/v1/league/players' },
    { path: '/onboarding/v1/league/teams', paginate: true },
    { path: `/onboarding/v1/league/competition/teams?competitionId=${compId}`, paginate: true },
    { path: `/gaming/v1/teamLineup/${compId}/${day.matchDay}/${day.championshipMatchDay}` },
  ]);
  const [players, leagueTeams, compTeams, lineups] = r.data;
  const res = await api(`/ext/v1/league/${$('fnLeague').value}/lineups/${target}`, {
    day,
    lineups: asList(lineups),
    competition_teams: compTeams.data,
    players: asList(players, 'players'),
    league_teams: leagueTeams.data,
    league_total: leagueTeams.item,
  });
  let msg = `${rosterSummary(res.roster_sync)}\nGiornata ${target} importata — squadre: ${res.managers_imported}.`;
  if (res.warnings && res.warnings.length) msg += `\nAvvisi (${res.warnings.length}):\n${res.warnings.join('\n')}`;
  show(msg.trim(), !!(res.warnings && res.warnings.length) || !!(res.roster_sync && res.roster_sync.error));
});

$('toggleSettings').onclick = () => { $('settings').hidden = !$('settings').hidden; };

$('saveSettings').onclick = () => busy(async () => {
  settings = { baseUrl: $('baseUrl').value.trim().replace(/\/+$/, ''), apiKey: $('apiKey').value.trim() };
  if (!/^https?:\/\//.test(settings.baseUrl) || !settings.apiKey) {
    show('Inserisci indirizzo (https://…) e chiave.', true);
    return;
  }
  await remember('settings', settings);
  $('settings').hidden = true;
  await loadMain();
});

(async () => {
  settings = (await chrome.storage.local.get('settings')).settings || {};
  $('baseUrl').value = settings.baseUrl || '';
  $('apiKey').value = settings.apiKey || '';
  if (!settings.baseUrl || !settings.apiKey) {
    $('settings').hidden = false;
    show('Configura indirizzo e chiave: la chiave si genera nell\'admin, pagina ⚽ Fantacalcio.');
    return;
  }
  await busy(loadMain);
})();
