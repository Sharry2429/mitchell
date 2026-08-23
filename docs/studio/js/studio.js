/**
 * Mitchell Studio — Master Application Controller
 * Handles WebSocket connection, panel routing, model cascade switcher,
 * and component lifecycle for IDE, Documents, Research, Smart Home, and Multi-Agent Floor.
 */

import { MitchellIDE } from './components/ide.js';
import { DocumentsStudio } from './components/documents.js';
import { DeepResearchStudio } from './components/research.js';
import { SmartHomeStudio } from './components/iot.js';
import { AgentsFloorStudio } from './components/agents_floor.js';

// ── Application State ──────────────────────────────────────────────────────
const state = {
  ws: null,
  connected: false,
  currentPanel: 'chat',
  status: 'idle',
  reconnectInterval: null,
  activeModel: 'grok-3',
  ideComponent: null,
  docsComponent: null,
  researchComponent: null,
  iotComponent: null,
  agentsComponent: null,
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
    console.log('Mitchell Studio WebSocket connected');
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
      console.log('WS message:', data);
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
  if (el) {
    el.innerHTML = connected
      ? '<span class="ws-dot connected"></span> Connected'
      : '<span class="ws-dot disconnected"></span> Disconnected';
  }
}

function updateStatus(status) {
  state.status = status;
  const indicator = document.getElementById('status-indicator');
  if (!indicator) return;
  const dot = indicator.querySelector('.status-dot');
  const text = indicator.querySelector('.status-text');

  if (dot) dot.className = 'status-dot ' + status;
  if (text) text.textContent = status.charAt(0).toUpperCase() + status.slice(1);

  // Update sidebar orb
  const orb = document.getElementById('sidebar-orb');
  if (orb) {
    if (status === 'thinking') {
      orb.style.animation = 'orb-breathe 0.8s ease-in-out infinite';
    } else if (status === 'working') {
      orb.style.animation = 'orb-breathe 0.4s ease-in-out infinite';
    } else {
      orb.style.animation = 'orb-breathe 3s ease-in-out infinite';
    }
  }
}

function updateCost(cost) {
  const el = document.getElementById('cost-display');
  if (el) el.textContent = cost.today_spent_inr || '₹0.00';
}

// ── Panel Navigation & Component Mounting ──────────────────────────────────
function switchPanel(panelId) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const panel = document.getElementById(`panel-${panelId}`);
  const navItem = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
  if (panel) panel.classList.add('active');
  if (navItem) navItem.classList.add('active');

  state.currentPanel = panelId;

  // Mount components on first view or reload
  if (panelId === 'ide') {
    if (!state.ideComponent) {
      state.ideComponent = new MitchellIDE('ide-content');
      state.ideComponent.render();
    }
  } else if (panelId === 'documents') {
    if (!state.docsComponent) {
      state.docsComponent = new DocumentsStudio('documents-content');
      state.docsComponent.render();
    }
  } else if (panelId === 'research') {
    if (!state.researchComponent) {
      state.researchComponent = new DeepResearchStudio('research-content');
      state.researchComponent.render();
    }
  } else if (panelId === 'home') {
    if (!state.iotComponent) {
      state.iotComponent = new SmartHomeStudio('home-content');
      state.iotComponent.render();
    }
  } else if (panelId === 'agents') {
    if (!state.agentsComponent) {
      state.agentsComponent = new AgentsFloorStudio('agents-content');
      state.agentsComponent.render();
    }
  } else if (panelId === 'workspace') {
    loadWorkspace();
  } else if (panelId === 'memory') {
    loadMemory();
  } else if (panelId === 'skills') {
    loadSkills();
  } else if (panelId === 'providers') {
    loadProviders();
  } else if (panelId === 'settings') {
    loadSettings();
  }
}

// ── Chat Logic ─────────────────────────────────────────────────────────────
function addMessage(role, content) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

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
    sendWS('message', { content: text, model: state.activeModel });
  } else {
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
        addMessage('assistant', `Error: ${err.message}. Is Studio server running?`);
      });
  }
}

// ── Generic Data Loaders ───────────────────────────────────────────────────
async function loadWorkspace() {
  const container = document.getElementById('workspace-content');
  try {
    const resp = await fetch('/api/workspace');
    const data = await resp.json();
    container.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));gap:12px;">
        <div class="card"><div class="card-title">Documents</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:#fff;">${data.documents || 0}</div></div>
        <div class="card"><div class="card-title">Spreadsheets</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:#fff;">${data.spreadsheets || 0}</div></div>
        <div class="card"><div class="card-title">Notes</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:#fff;">${data.notes || 0}</div></div>
        <div class="card"><div class="card-title">Projects</div><div class="card-subtitle" style="font-size:18px;font-weight:700;color:#fff;">${data.project_boards || 0}</div></div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function loadMemory() {
  const container = document.getElementById('memory-content');
  try {
    const resp = await fetch('/api/memory');
    const data = await resp.json();
    container.innerHTML = `<div class="card"><pre><code>${JSON.stringify(data.self_model || {}, null, 2)}</code></pre></div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function loadSkills() {
  const container = document.getElementById('skills-content');
  try {
    const resp = await fetch('/api/skills');
    const data = await resp.json();
    const skills = data.skills || [];
    let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));gap:12px;">';
    for (const s of skills) {
      html += `
        <div class="card">
          <div class="card-title">${s.name}</div>
          <div class="card-subtitle">${s.description}</div>
        </div>
      `;
    }
    html += '</div>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function loadProviders() {
  const container = document.getElementById('providers-content');
  try {
    const resp = await fetch('/api/providers');
    const data = await resp.json();
    const providers = data.providers || [];
    let html = '<div class="provider-grid">';
    for (const p of providers) {
      html += `
        <div class="card">
          <div class="card-title">${p.name} <span class="badge ${p.is_healthy ? 'badge-green' : 'badge-red'}">${p.is_healthy ? 'Healthy' : 'Down'}</span></div>
          <div class="card-subtitle">Tier: ${p.is_free_tier ? 'Free' : 'Paid'} • Latency: ${p.avg_latency_ms || 0}ms</div>
        </div>
      `;
    }
    html += '</div>';
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

async function loadSettings() {
  const container = document.getElementById('settings-content');
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    let html = '';
    for (const [k, v] of Object.entries(data)) {
      html += `<div class="card"><div class="card-title">${k}</div><div class="card-subtitle">${JSON.stringify(v)}</div></div>`;
    }
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
  }
}

// ── Action Handlers: Take Over & Teach Me ──────────────────────────────────
function handleTakeover() {
  const goal = prompt('Enter project or task goal for Mitchell to take over autonomously:');
  if (!goal) return;

  fetch('/api/takeover', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'start', goal: goal }),
  })
    .then(r => r.json())
    .then(session => {
      switchPanel('agents');
      addMessage('assistant', `<strong>Autonomous Takeover Initialized:</strong> "${goal}"\nSession ID: <code>${session.session_id}</code>\nMitchell is coordinating agents across workspace.`);
    })
    .catch(e => alert(`Takeover failed: ${e.message}`));
}

function handleTeachMe() {
  const skillName = prompt('Enter name of the skill/task you want to teach Mitchell:');
  if (!skillName) return;

  const demoAction = prompt('Enter target tool or demonstration note for this skill (e.g. browser_goto, windows_type_text):', 'browser_goto');

  fetch('/api/teaching', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'synthesize',
      name: skillName,
      description: `User demonstrated procedure for ${skillName}`,
      actions: [
        { action_type: 'tool', target: demoAction || 'browser_goto', params: { url: 'https://example.com' } }
      ],
    }),
  })
    .then(r => r.json())
    .then(res => {
      switchPanel('skills');
      addMessage('assistant', `<strong>Skill Synthesized Successfully!</strong>\nMitchell has learned: <code>${res.skill_name}</code> (${res.steps_count} steps).\nParameters: <code>${res.parameters.join(', ')}</code>`);
    })
    .catch(e => alert(`Teaching failed: ${e.message}`));
}

// ── DOM Initialization ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Navigation
  document.querySelectorAll('.nav-item[data-panel]').forEach(btn => {
    btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
  });

  // Sidebar toggle
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    document.getElementById('sidebar')?.classList.toggle('collapsed');
  });

  // Model cascade selector
  const modelSelect = document.getElementById('global-model-selector');
  modelSelect?.addEventListener('change', () => {
    state.activeModel = modelSelect.value;
    const disp = document.getElementById('model-display');
    if (disp) disp.textContent = modelSelect.options[modelSelect.selectedIndex].text;
  });

  // Action buttons
  document.getElementById('topbar-takeover-btn')?.addEventListener('click', handleTakeover);
  document.getElementById('topbar-teach-btn')?.addEventListener('click', handleTeachMe);

  // Chat input
  const chatInput = document.getElementById('chat-input');
  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });
  document.getElementById('chat-send')?.addEventListener('click', sendChat);

  // Global search shortcut (Ctrl+K)
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
      if (target === 'workspace') loadWorkspace();
      if (target === 'memory') loadMemory();
      if (target === 'skills') loadSkills();
      if (target === 'providers') loadProviders();
    });
  });

  // Quick action chips
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const panelTarget = chip.dataset.panelTarget;
      const chipAction = chip.dataset.chip;
      if (panelTarget) {
        switchPanel(panelTarget);
      } else if (chipAction === 'takeover') {
        handleTakeover();
      } else if (chipAction === 'teach') {
        handleTeachMe();
      }
    });
  });

  // Connect WebSocket
  connectWS();
});

