// Chronicles of Darkness Combat Simulator — frontend
'use strict';

// ─── State ────────────────────────────────────────────────────────────────────
let builds = [];
let activeStream = null;

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadStatus();
  await loadBuilds();
  showPanel('leaderboard');
});

// ─── Navigation ───────────────────────────────────────────────────────────────
function showPanel(id) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  document.querySelector(`nav button[data-panel="${id}"]`).classList.add('active');

  if (id === 'leaderboard') renderLeaderboard();
  if (id === 'combat') populateBuildSelects();
}

document.querySelectorAll('nav button').forEach(btn => {
  btn.addEventListener('click', () => showPanel(btn.dataset.panel));
});

// ─── Status ───────────────────────────────────────────────────────────────────
async function loadStatus() {
  try {
    const r = await fetch('/api/status');
    const s = await r.json();
    document.getElementById('status-bar').textContent =
      `${s.builds} builds · ${s.ratings} rated · policy ${s.policy ? '✓' : '✗'}`;
  } catch {}
}

// ─── Builds ───────────────────────────────────────────────────────────────────
async function loadBuilds() {
  const r = await fetch('/api/builds');
  builds = await r.json();
}

function splatBadge(splat) {
  return `<span class="badge badge-${splat}">${splat}</span>`;
}

// ─── Leaderboard ──────────────────────────────────────────────────────────────
async function renderLeaderboard() {
  const splatFilter = document.getElementById('filter-splat').value;
  const url = '/api/ratings/leaderboard?n=50' + (splatFilter ? `&splat=${splatFilter}` : '');
  const r = await fetch(url);
  const rows = await r.json();

  const maxR = rows.reduce((m, x) => Math.max(m, x.r), 1);
  const minR = rows.reduce((m, x) => Math.min(m, x.r), 1500);
  const range = maxR - minR || 1;

  const tbody = document.getElementById('lb-body');
  tbody.innerHTML = rows.map(row => {
    const barWidth = Math.max(4, Math.round(80 * (row.r - minR) / range));
    return `
      <tr>
        <td>${row.rank}</td>
        <td><strong>${escHtml(row.name)}</strong></td>
        <td>${splatBadge(row.splat)}</td>
        <td>
          <span class="rating-bar" style="width:${barWidth}px"></span>
          ${row.r.toFixed(0)}
        </td>
        <td style="color:var(--muted)">${row.RD.toFixed(0)}</td>
        <td style="color:var(--muted)">${row.n_matches}</td>
      </tr>`;
  }).join('');
}

document.getElementById('filter-splat').addEventListener('change', renderLeaderboard);

// ─── Combat Simulator ─────────────────────────────────────────────────────────
function populateBuildSelects() {
  ['build-a', 'build-b'].forEach((id, ti) => {
    const sel = document.getElementById(id);
    const prev = sel.value;
    sel.innerHTML = builds.map(b =>
      `<option value="${b.id}">${b.name} (${b.splat})</option>`
    ).join('');
    if (prev) sel.value = prev;
    // Default: pick different builds for each side
    if (!prev && builds.length > ti) sel.value = builds[ti].id;
    sel.dispatchEvent(new Event('change'));
  });
}

function getBuildById(id) {
  return builds.find(b => b.id == id);
}

function renderBuildStats(build, containerId) {
  if (!build) return;
  document.getElementById(containerId).innerHTML = `
    <div>${splatBadge(build.splat)}</div>
    <div style="margin-top:0.5rem">
      HP <span>${build.derived.max_health}</span> ·
      WP <span>${build.derived.max_willpower}</span>
      ${build.derived.max_resource ? `· Resource <span>${build.derived.max_resource}</span>` : ''}
    </div>
    <div>
      Str <span>${build.attributes.strength}</span> ·
      Dex <span>${build.attributes.dexterity}</span> ·
      Sta <span>${build.attributes.stamina}</span>
    </div>
    <div>
      Brawl <span>${build.skills.brawl}</span> ·
      Weapon <span>${build.skills.weaponry}</span> ·
      Firearms <span>${build.skills.firearms}</span>
    </div>
    ${renderSplatDetails(build)}
  `;
}

function renderSplatDetails(build) {
  const d = build.splat_details;
  if (!d || Object.keys(d).length === 0) return '';
  if (build.splat === 'vampire') {
    return `<div>BP <span>${d.blood_potency}</span> · Cel <span>${d.celerity}</span> · Vig <span>${d.vigor}</span> · Res <span>${d.resilience}</span></div>`;
  }
  if (build.splat === 'werewolf') {
    return `<div>Primal Urge <span>${d.primal_urge}</span></div>`;
  }
  if (build.splat === 'changeling') {
    return `<div>Wyrd <span>${d.wyrd}</span> · Seeming <span>${d.seeming}</span></div>`;
  }
  return '';
}

document.getElementById('build-a').addEventListener('change', e => {
  renderBuildStats(getBuildById(e.target.value), 'stats-a');
});
document.getElementById('build-b').addEventListener('change', e => {
  renderBuildStats(getBuildById(e.target.value), 'stats-b');
});

// ─── Combat execution ─────────────────────────────────────────────────────────
document.getElementById('btn-run').addEventListener('click', runCombat);
document.getElementById('btn-stream').addEventListener('click', streamCombat);
document.getElementById('btn-stop').addEventListener('click', stopStream);

async function runCombat() {
  const bidA = parseInt(document.getElementById('build-a').value);
  const bidB = parseInt(document.getElementById('build-b').value);
  const seed = parseInt(document.getElementById('seed-input').value) || 0;

  setRunning(true);
  clearLog();

  try {
    const r = await fetch('/api/combat/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({build_id_a: bidA, build_id_b: bidB, seed, use_policy: true}),
    });
    const log = await r.json();

    // Initialize health track display
    initCombatHeader(log.build_a, log.build_b, log);

    // Replay all events
    for (const ev of log.events) {
      appendLogEntry(ev);
      if (ev.is_terminal || ev === log.events[log.events.length - 1]) {
        updateCombatHeader(ev.characters);
      }
    }

    showResult(log);
  } catch (e) {
    document.getElementById('stream-status').textContent = 'Error: ' + e.message;
  } finally {
    setRunning(false);
  }
}

function streamCombat() {
  if (activeStream) stopStream();

  const bidA = parseInt(document.getElementById('build-a').value);
  const bidB = parseInt(document.getElementById('build-b').value);
  const seed = parseInt(document.getElementById('seed-input').value) || 0;
  const delay = parseInt(document.getElementById('delay-input').value) || 150;

  setRunning(true, true);
  clearLog();

  const url = `/api/combat/stream?build_id_a=${bidA}&build_id_b=${bidB}&seed=${seed}&delay_ms=${delay}&use_policy=true`;
  activeStream = new EventSource(url);
  let step = 0;

  activeStream.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'meta') {
      initCombatHeader(data.build_a, data.build_b);
    } else if (data.type === 'step') {
      step++;
      appendLogEntry(data);
      updateCombatHeader(data.characters);
      document.getElementById('stream-status').textContent =
        `Step ${step}, Turn ${data.turn} — streaming…`;
    } else if (data.type === 'done') {
      showResult(data);
      stopStream();
    }
  };

  activeStream.onerror = () => {
    document.getElementById('stream-status').textContent = 'Stream ended.';
    stopStream();
  };
}

function stopStream() {
  if (activeStream) {
    activeStream.close();
    activeStream = null;
  }
  setRunning(false);
}

// ─── UI helpers ───────────────────────────────────────────────────────────────
function setRunning(running, isStream = false) {
  document.getElementById('btn-run').disabled = running;
  document.getElementById('btn-stream').disabled = running;
  document.getElementById('btn-stop').style.display = (running && isStream) ? '' : 'none';
  if (!running) {
    document.getElementById('stream-status').textContent = '';
  }
}

function clearLog() {
  document.getElementById('combat-log').innerHTML = '';
  document.getElementById('combat-output').querySelector('.result-banner')?.remove();
  document.getElementById('stream-status').textContent = '';
}

function initCombatHeader(buildA, buildB, log = null) {
  const initialChars = log ? log.events[0]?.characters : null;
  document.getElementById('combat-header').innerHTML = `
    <div class="combatant-header">
      <h4 style="color:#6db3f2">${escHtml(buildA.name)} ${splatBadge(buildA.splat)}</h4>
      <div class="health-track" id="ht-0"></div>
      <div class="stats-row" id="sr-0">WP — · Res —</div>
    </div>
    <div class="combatant-header">
      <h4 style="color:#f27676">${escHtml(buildB.name)} ${splatBadge(buildB.splat)}</h4>
      <div class="health-track" id="ht-1"></div>
      <div class="stats-row" id="sr-1">WP — · Res —</div>
    </div>`;

  if (initialChars) updateCombatHeader(initialChars);
}

function updateCombatHeader(chars) {
  chars.forEach((ch, i) => {
    const ht = document.getElementById(`ht-${i}`);
    if (!ht) return;
    const boxes = [];
    for (let j = 0; j < ch.max_health; j++) {
      let cls = '';
      if (j < ch.aggravated) cls = 'aggravated';
      else if (j < ch.aggravated + ch.lethal) cls = 'lethal';
      else if (j < ch.aggravated + ch.lethal + ch.bashing) cls = 'bashing';
      boxes.push(`<div class="hp-box ${cls}"></div>`);
    }
    ht.innerHTML = boxes.join('');

    const sr = document.getElementById(`sr-${i}`);
    if (sr) {
      sr.innerHTML = `WP <span>${ch.willpower}</span> · Res <span>${ch.resource}</span>` +
        (ch.is_incap ? ' · <span style="color:var(--accent)">INCAP</span>' : '');
    }
  });
}

function appendLogEntry(ev) {
  const log = document.getElementById('combat-log');
  const div = document.createElement('div');
  div.className = 'log-entry';
  div.innerHTML = `
    <span class="log-turn">${ev.turn}</span>
    <span class="log-actor team-${ev.actor_team}">${escHtml(ev.actor_name)}</span>
    <span class="log-action">${escHtml(ev.action_desc)}</span>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function showResult(data) {
  const out = document.getElementById('combat-output');
  const banner = document.createElement('div');
  const winner = data.winner_team;
  const name = data.winner_name;
  if (winner === 0) {
    banner.className = 'result-banner team-0';
    banner.textContent = `${name} wins in ${data.n_turns} turns`;
  } else if (winner === 1) {
    banner.className = 'result-banner team-1';
    banner.textContent = `${name} wins in ${data.n_turns} turns`;
  } else {
    banner.className = 'result-banner draw';
    banner.textContent = `Draw after ${data.n_turns} turns`;
  }
  out.appendChild(banner);
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
