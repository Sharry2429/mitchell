/**
 * Mitchell Studio — Main Application Logic
 * Handles WebSocket connection, panel navigation, chat, and dynamic data loading.
 */

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  ws: null,
  connected: false,
  currentPanel: 'chat',
  status: 'idle',
  reconnectInterval: null,
  providers: [],
};

// ── WebSocket ──────────────────────────────────────────────────────────────
function connectWS() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws`;

  try {
    state.ws = new WebSocket(wsUrl);
  } catch (e) {
    console.warn('WebSocket connection failed:', e);
    updateWSStatus(false);
    scheduleReconnect();
    return;
  }

  state.ws.onopen = () => {
    state.connected = true;
    updateWSStatus(true);
    if (state.reconnectInterval) {
      clearInterval(state.reconnectInterval);
      state.reconnectInterval = null;
    }
    console.log('Studio WebSocket connected');
  };

  state.ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWSMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };

  state.ws.onclose = () => {
    state.connected = false;
    updateWSStatus(false);
    scheduleReconnect();
  };

  state.ws.onerror = () => {
    state.connected = false;
    updateWSStatus(false);
  };
}

function scheduleReconnect() {
  if (!state.reconnectInterval) {
    state.reconnectInterval = setInterval(connectWS, 3000);
  }
}

function handleWSMessage(data) {
  switch (data.type) {
    case 'init':
      updateStatus(data.status || 'idle');
      if (data.cost) updateCost(data.cost);
      if (data.providers) state.providers = data.providers;
      break;
    case 'status':
      updateStatus(data.status);
      break;
    case 'response':
    case 'chat_response':
      addMessage('assistant', data.content);
      if (data.status) updateStatus(data.status);
      if (data.duration) {
        document.getElementById('token-count').textContent = `${data.duration}s`;
      }
      break;
    case 'state':
      if (data.cost) updateCost(data.cost);
      break;
    case 'pong':
      break;
    default:
      console.log('Unknown WS message type:', data.type);
  }
}

function sendWS(type, payload = {}) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify({ type, ...payload }));
  }
}

// ── UI Updates ─────────────────────────────────────────────────────────────
function updateWSStatus(connected) {
  const el = document.getElementById('ws-status');
  if (connected) {
    el.innerHTML = '<span class="ws-dot connected"></span> Connected';
  } else {
    el.innerHTML = '<span class="ws-dot disconnected"></span> Disconnected';
  }
}

function updateStatus(status) {
  state.status = status;
  const indicator = document.getElementById('status-indicator');
  const dot = indicator.querySelector('.status-dot');
  const text = indicator.querySelector('.status-text');

  dot.className = 'status-dot ' + status;
  text.textContent = status.charAt(0).toUpperCase() + status.slice(1);

  // Update sidebar orb
  const orb = document.getElementById('sidebar-orb');
  if (orb) {
    if (status === 'thinking') {
      orb.style.animation = 'orb-breathe 0.8s ease-in-out infinite';
    } else if (status === 'working') {
      orb.style.animation = 'orb-breathe 0.5s ease-in-out infinite';
    } else {
      orb.style.animation = 'orb-breathe 3s ease-in-out infinite';
    }
  }
}

function updateCost(cost) {
  const el = document.getElementById('cost-display');
  if (el) el.textContent = cost.today_spent_inr || '₹0.00';
}

// ── Panel Navigation ───────────────────────────────────────────────────────
function switchPanel(panelId) {
  // Deactivate all
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  // Activate target
  const panel = document.getElementById(`panel-${panelId}`);
  const navItem = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
  if (panel) panel.classList.add('active');
  if (navItem) navItem.classList.add('active');

  state.currentPanel = panelId;

  // Load data for panels that need it
  if (panelId === 'providers') loadProviders();
  if (panelId === 'memory') loadMemory();
  if (panelId === 'skills') loadSkills();
  if (panelId === 'agents') loadAgents();
  if (panelId === 'settings') loadSettings();
  if (panelId === 'workspace') loadWorkspace('overview');
  if (panelId === 'ide') loadIDE();
}

// ── Chat ───────────────────────────────────────────────────────────────────
function addMessage(role, content) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.innerHTML = role === 'assistant'
    ? '<i class="fa-solid fa-robot"></i>'
    : '<i class="fa-solid fa-user"></i>';

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  const textDiv = document.createElement('div');
  textDiv.className = 'message-text';
  textDiv.innerHTML = formatMessage(content);
  contentDiv.appendChild(textDiv);

  msg.appendChild(avatar);
  msg.appendChild(contentDiv);
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function formatMessage(text) {
  // Basic markdown-like formatting
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function sendChat() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  addMessage('user', text);
  input.value = '';
  input.style.height = 'auto';

  if (state.connected) {
    sendWS('message', { content: text });
  } else {
    // Fallback: use REST API
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })
      .then(r => r.json())
      .then(data => {
        addMessage('assistant', data.response);
        if (data.cost) updateCost(data.cost);
      })
      .catch(err => {
        addMessage('assistant', `Error: ${err.message}. Is the Studio server running?`);
      });
  }
}

// ── Data Loaders ───────────────────────────────────────────────────────────
async function loadProviders() {
  try {
    const resp = await fetch('/api/providers');
    const data = await resp.json();
    renderProviders(data);
  } catch (e) {
    document.getElementById('providers-content').innerHTML =
      '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>Failed to load providers</p></div>';
  }
}

function renderProviders(data) {
  const container = document.getElementById('providers-content');
  const providers = data.providers || [];
  if (!providers.length) {
    container.innerHTML = '<div class="empty-state"><p>No providers configured</p></div>';
    return;
  }

  let html = '<div class="provider-grid">';
  for (const p of providers) {
    const statusBadge = p.is_healthy
      ? '<span class="badge badge-green">Healthy</span>'
      : '<span class="badge badge-red">Unhealthy</span>';
    const freeBadge = p.is_free_tier
      ? '<span class="badge badge-blue">Free Tier</span>'
      : '<span class="badge badge-yellow">Paid</span>';
    const keyBadge = p.has_api_key
      ? '<span class="badge badge-green">Key Set</span>'
      : '<span class="badge badge-red">No Key</span>';

    html += `
      <div class="provider-card ${p.enabled ? '' : 'disabled'}">
        <div class="provider-header">
          <span class="provider-name">${p.display_name}</span>
          ${statusBadge}
        </div>
        <div class="card-subtitle">${p.models.length} models • ${p.avg_latency_ms}ms avg • ${p.success_rate}% success</div>
        <div class="provider-meta">
          ${freeBadge} ${keyBadge}
          <span class="badge badge-purple">${p.total_requests} requests</span>
        </div>
      </div>
    `;
  }
  html += '</div>';
  container.innerHTML = html;
}

async function loadMemory() {
  try {
    const resp = await fetch('/api/memory');
    const data = await resp.json();
    renderMemory(data);
  } catch (e) {
    document.getElementById('memory-tab-content').innerHTML =
      '<div class="empty-state"><p>Failed to load memory data</p></div>';
  }
}

function renderMemory(data) {
  const container = document.getElementById('memory-tab-content');
  const capabilities = data.self_model?.capabilities || [];

  if (!capabilities.length) {
    container.innerHTML = '<div class="empty-state"><p>No capabilities recorded yet</p></div>';
    return;
  }

  let html = '';
  for (const cap of capabilities) {
    const confColor = cap.confidence >= 0.8 ? 'badge-green' : cap.confidence >= 0.5 ? 'badge-yellow' : 'badge-red';
    html += `
      <div class="card">
        <div class="card-title">${cap.capability_name}</div>
        <div class="card-subtitle">
          ${cap.category} • ${cap.total_runs} runs •
          <span class="badge ${confColor}">${Math.round(cap.confidence * 100)}% conf</span>
          <span class="badge badge-blue">${cap.success_rate || 100}% success</span>
        </div>
        ${cap.known_gaps?.length ? `<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">Gaps: ${cap.known_gaps.join(', ')}</div>` : ''}
      </div>
    `;
  }
  container.innerHTML = html;
}

let currentSkillTab = 'skills';

async function loadSkills(tab) {
  if (tab) currentSkillTab = tab;
  const container = document.getElementById('skills-content');
  container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';

  if (currentSkillTab === 'skills') {
    try {
      const resp = await fetch('/api/skills');
      const data = await resp.json();
      renderSkills(data);
    } catch (e) {
      container.innerHTML = '<div class="empty-state"><p>Failed to load skills</p></div>';
    }
  } else if (currentSkillTab === 'marketplace') {
    try {
      const resp = await fetch('/api/plugins');
      const data = await resp.json();
      renderMarketplace(data);
    } catch (e) {
      container.innerHTML = '<div class="empty-state"><p>Failed to load marketplace</p></div>';
    }
  } else if (currentSkillTab === 'mcp') {
    try {
      const resp = await fetch('/api/mcp');
      const data = await resp.json();
      renderMCP(data);
    } catch (e) {
      container.innerHTML = '<div class="empty-state"><p>Failed to load MCP servers</p></div>';
    }
  }
}

function renderSkills(data) {
  const container = document.getElementById('skills-content');
  const skills = data.skills || [];
  if (!skills.length) {
    container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-wand-magic-sparkles"></i><p>No procedural skills registered yet</p></div>';
    return;
  }

  let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;">';
  for (const s of skills) {
    html += `
      <div class="card" style="margin-bottom:0">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span class="card-title" style="margin:0">${s.name}</span>
          <span class="badge badge-purple">v${s.version || '1.0'}</span>
        </div>
        <div class="card-subtitle" style="font-size:12px;margin-bottom:8px">${s.description || 'Procedural workflow.'}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--text-muted)">
          <span>Source: <strong style="color:var(--text-main)">${s.source || 'organic'}</strong></span>
          <span class="badge badge-green">${Math.round((s.confidence || 0.8) * 100)}% conf</span>
        </div>
      </div>
    `;
  }
  html += '</div>';
  container.innerHTML = html;
}

function renderMarketplace(data) {
  const container = document.getElementById('skills-content');
  const marketplace = data.marketplace || [];
  if (!marketplace.length) {
    container.innerHTML = '<div class="empty-state"><p>No marketplace plugins found</p></div>';
    return;
  }

  let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">';
  for (const p of marketplace) {
    const isInstalled = p.installed;
    html += `
      <div class="card" style="margin-bottom:0;display:flex;flex-direction:column;justify-content:space-between">
        <div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span class="card-title" style="margin:0">${p.name}</span>
            <div>
              ${p.has_mcp ? '<span class="badge badge-blue">MCP</span>' : ''}
              ${isInstalled ? '<span class="badge badge-green">Installed</span>' : '<span class="badge badge-yellow">Official</span>'}
            </div>
          </div>
          <div class="card-subtitle" style="font-size:12px;margin-bottom:8px">${p.description}</div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05)">
          <span style="font-size:11px;color:var(--text-muted)">${p.author || 'Anthropic'}</span>
          <button class="topbar-btn" style="font-size:11px;padding:4px 10px;height:auto;background:${isInstalled ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)'};color:${isInstalled ? '#ef4444' : '#22c55e'}" onclick="togglePluginInstall('${p.name}', ${isInstalled})">
            ${isInstalled ? 'Uninstall' : '<i class="fa-solid fa-download"></i> Install'}
          </button>
        </div>
      </div>
    `;
  }
  html += '</div>';
  container.innerHTML = html;
}

async function togglePluginInstall(name, isInstalled) {
  try {
    const action = isInstalled ? 'uninstall' : 'install';
    const resp = await fetch('/api/plugins', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, plugin: name }),
    });
    const res = await resp.json();
    alert(res.message || (res.success ? 'Success!' : res.error));
    loadSkills('marketplace');
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function renderMCP(data) {
  const container = document.getElementById('skills-content');
  const servers = data.servers || [];
  if (!servers.length) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-server"></i>
        <p>No external MCP servers connected.</p>
        <div style="margin-top:8px;font-size:12px;color:var(--text-muted)">Connect via CLI: <code>mitchell mcp add &lt;name&gt; &lt;cmd&gt;</code> or install an official plugin.</div>
      </div>
    `;
    return;
  }

  let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;">';
  for (const s of servers) {
    html += `
      <div class="card" style="margin-bottom:0">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span class="card-title" style="margin:0">${s.server_name}</span>
          <span class="badge ${s.is_connected ? 'badge-green' : 'badge-red'}">${s.is_connected ? 'Active' : 'Offline'}</span>
        </div>
        <div class="card-subtitle" style="font-size:12px;margin-bottom:8px">Bridged Tools (${s.tool_count}):</div>
        <div style="font-family:monospace;font-size:11px;color:var(--text-muted)">
          ${(s.tools || []).join(', ') || 'No tools exported'}
        </div>
      </div>
    `;
  }
  html += '</div>';
  container.innerHTML = html;
}

async function loadAgents() {
  try {
    const resp = await fetch('/api/agents');
    const data = await resp.json();
    renderAgents(data);
  } catch (e) {
    document.getElementById('agents-content').innerHTML =
      '<div class="empty-state"><p>Failed to load agents</p></div>';
  }
}

function renderAgents(data) {
  const container = document.getElementById('agents-content');
  const agents = data.agents || [];
  if (!agents.length) {
    container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-diagram-project"></i><p>No agents registered</p></div>';
    return;
  }

  let html = '';
  for (const a of agents) {
    html += `
      <div class="card">
        <div class="card-title">${a.agent_id}</div>
        <div class="card-subtitle">${a.description || 'Hive Agent'}</div>
      </div>
    `;
  }
  container.innerHTML = html;
}

async function loadSettings() {
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    renderSettings(data);
  } catch (e) {
    document.getElementById('settings-content').innerHTML =
      '<div class="empty-state"><p>Failed to load settings</p></div>';
  }
}

function renderSettings(data) {
  const container = document.getElementById('settings-content');
  let html = '<div class="card"><div class="card-title">System Configuration</div></div>';
  for (const [key, value] of Object.entries(data)) {
    html += `
      <div class="card">
        <div class="card-title">${key}</div>
        <div class="card-subtitle">${JSON.stringify(value)}</div>
      </div>
    `;
  }
  container.innerHTML = html;
}

// ── Workspace Loader & Renderer ───────────────────────────────────────────
async function loadWorkspace(section = 'overview') {
  const container = document.getElementById('workspace-content');
  container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';
  try {
    const resp = await fetch(`/api/workspace?section=${section === 'overview' ? 'summary' : section}`);
    const data = await resp.json();
    renderWorkspace(section, data);
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>Failed to load workspace data</p></div>';
  }
}

function renderWorkspace(section, data) {
  const container = document.getElementById('workspace-content');
  if (section === 'overview') {
    container.innerHTML = `
      <div class="provider-grid">
        <div class="card"><div class="card-title"><i class="fa-solid fa-file-lines" style="color:var(--accent-purple)"></i> Documents</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:var(--text-primary);margin-top:4px">${data.documents || 0}</div></div>
        <div class="card"><div class="card-title"><i class="fa-solid fa-table" style="color:var(--accent-green)"></i> Spreadsheets</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:var(--text-primary);margin-top:4px">${data.spreadsheets || 0}</div></div>
        <div class="card"><div class="card-title"><i class="fa-solid fa-note-sticky" style="color:var(--accent-yellow)"></i> Notes & Knowledge</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:var(--text-primary);margin-top:4px">${data.notes || 0}</div></div>
        <div class="card"><div class="card-title"><i class="fa-solid fa-list-check" style="color:var(--accent-blue)"></i> Projects & Boards</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:var(--text-primary);margin-top:4px">${data.project_boards || 0}</div></div>
      </div>
      <div class="card" style="margin-top:16px"><div class="card-title">Quick Tip</div><div class="card-subtitle">Ask Mitchell in chat to create documents, analyze CSV spreadsheets, add notes with [[WikiLinks]], or manage Kanban tasks!</div></div>
    `;
  } else if (section === 'documents') {
    const docs = data.documents || [];
    if (!docs.length) { container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-file-circle-plus"></i><p>No documents yet. Ask Mitchell to draft a report or document.</p></div>'; return; }
    let html = '';
    for (const d of docs) {
      html += `<div class="card"><div class="card-title"><i class="fa-solid fa-file-lines" style="color:var(--accent-purple);margin-right:6px"></i>${d.title}</div><div class="card-subtitle">${d.path} • ${d.size_bytes} bytes</div></div>`;
    }
    container.innerHTML = html;
  } else if (section === 'notes') {
    const notes = data.notes || [];
    if (!notes.length) { container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-note-sticky"></i><p>No linked notes. Use [[Note Title]] in any note to link concepts.</p></div>'; return; }
    let html = '';
    for (const n of notes) {
      html += `<div class="card"><div class="card-title"><i class="fa-solid fa-note-sticky" style="color:var(--accent-yellow);margin-right:6px"></i>${n.title}</div><div class="card-subtitle">Links: ${n.outgoing_links?.join(', ') || 'None'} • Backlinks: ${n.backlinks_count}</div></div>`;
    }
    container.innerHTML = html;
  } else if (section === 'projects') {
    const projects = data.projects || [];
    if (!projects.length) { container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-list-check"></i><p>No project boards yet. Ask Mitchell to scaffold a task board.</p></div>'; return; }
    let html = '';
    for (const p of projects) {
      html += `<div class="card"><div class="card-title"><i class="fa-solid fa-list-check" style="color:var(--accent-blue);margin-right:6px"></i>${p.title}</div><div class="card-subtitle">${p.progress?.completed || 0}/${p.progress?.total || 0} tasks completed (${p.progress?.percent || 0}%)</div></div>`;
    }
    container.innerHTML = html;
  } else {
    container.innerHTML = `<div class="card"><pre><code>${JSON.stringify(data, null, 2)}</code></pre></div>`;
  }
}

// ── IDE Loader & Renderer ─────────────────────────────────────────────────
async function loadIDE() {
  const container = document.getElementById('ide-content');
  container.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading IDE environment...</div>';
  try {
    const resp = await fetch('/api/ide');
    const data = await resp.json();
    renderIDE(data);
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><p>Failed to load IDE data</p></div>';
  }
}

function renderIDE(data) {
  const container = document.getElementById('ide-content');
  const projects = data.projects || [];
  const tools = data.tools || [];

  let html = `
    <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;">
      <h3 style="font-size:14px;color:var(--text-primary)"><i class="fa-solid fa-laptop-code" style="color:var(--accent-purple);margin-right:6px"></i>Active Projects</h3>
    </div>
  `;

  if (projects.length) {
    html += '<div class="provider-grid" style="margin-bottom:20px;">';
    for (const p of projects) {
      html += `
        <div class="card">
          <div class="card-title">${p.name} <span class="badge badge-purple">${p.project_type}</span></div>
          <div class="card-subtitle">${p.root_path}</div>
        </div>
      `;
    }
    html += '</div>';
  } else {
    html += '<div class="card" style="margin-bottom:20px;"><div class="card-subtitle">No IDE projects yet. Mitchell can scaffold Python, Node, or Web projects automatically.</div></div>';
  }

  html += `
    <h3 style="font-size:14px;color:var(--text-primary);margin-bottom:12px;"><i class="fa-solid fa-screwdriver-wrench" style="color:var(--accent-green);margin-right:6px"></i>External Tool Bridges</h3>
    <div class="provider-grid">
  `;

  for (const t of tools) {
    const badge = t.installed ? '<span class="badge badge-green">Installed</span>' : '<span class="badge badge-red">Missing</span>';
    html += `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div class="card-title">${t.name}</div>
          ${badge}
        </div>
        <div class="card-subtitle">${t.description}</div>
      </div>
    `;
  }
  html += '</div>';

  container.innerHTML = html;
}

// ── Event Listeners ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Panel navigation
  document.querySelectorAll('.nav-item[data-panel]').forEach(item => {
    item.addEventListener('click', () => switchPanel(item.dataset.panel));
  });

  // Sidebar toggle
  const sidebar = document.getElementById('sidebar');
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });

  // Chat input
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');

  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });

  // Auto-resize textarea
  chatInput?.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  sendBtn?.addEventListener('click', sendChat);

  // Global search shortcut
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      document.getElementById('global-search')?.focus();
    }
  });

  // Refresh buttons
  document.querySelectorAll('.refresh-btn[data-refresh]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.refresh;
      if (target === 'providers') loadProviders();
      if (target === 'memory') loadMemory();
      if (target === 'skills') loadSkills();
      if (target === 'agents') loadAgents();
      if (target === 'workspace') loadWorkspace('overview');
      if (target === 'ide') loadIDE();
    });
  });

  // Memory tabs
  document.querySelectorAll('.tab-btn[data-tab]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn[data-tab]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
    });
  });

  // Workspace sub-tabs
  document.querySelectorAll('.tab-btn[data-wstab]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn[data-wstab]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadWorkspace(tab.dataset.wstab);
    });
  });

  // Skills / Plugins / MCP sub-tabs
  document.querySelectorAll('.tab-btn[data-skilltab]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn[data-skilltab]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      loadSkills(tab.dataset.skilltab);
    });
  });

  // Connect WebSocket
  connectWS();

  // Periodic state refresh
  setInterval(() => {
    if (state.connected) {
      sendWS('ping');
    }
  }, 30000);
});
