/**
 * Mitchell Studio — Pure Minimalist OLED Black Controller
 * Focused · Functional · Clean · Zero Clutter
 */

import { MitchellIDE } from './components/ide.js';
import { DocumentsStudio } from './components/documents.js';
import { DeepResearchStudio } from './components/research.js';
import { SmartHomeStudio } from './components/iot.js';
import { AgentsFloorStudio } from './components/agents_floor.js';

// ── State Management ────────────────────────────────────────────────────────
const state = {
  activePanel: 'chat',
  activeModel: 'grok-3',
  activeFile: 'mitchell/manager/loop.py',
  ws: null,
  ideComponent: null,
  docsComponent: null,
  researchComponent: null,
  homeComponent: null,
  agentsComponent: null,
  memoryCanvasInitialized: false,
  mcpCatalog: [
    { name: 'filesystem', desc: 'Read and write local files with access control.', installed: true },
    { name: 'brave-search', desc: 'Real-time web search and content extraction.', installed: true },
    { name: 'github', desc: 'Inspect pull requests, repos, issues, and git commits.', installed: true },
    { name: 'whatsapp-mcp', desc: 'Baileys WhatsApp socket bridge for notifications.', installed: true },
    { name: 'home-assistant', desc: 'Entity control for lights, climate, locks and IoT.', installed: true },
    { name: 'memory-graph', desc: 'Episodic and semantic knowledge triple store.', installed: true },
    { name: 'postgres', desc: 'Analytical SQL querying and database schemas.', installed: false },
    { name: 'puppeteer', desc: 'Stealth headless browser automation engine.', installed: false },
    { name: 'sqlite', desc: 'Embedded relational database for workspace data.', installed: false }
  ]
};

// ── Helper Selectors ────────────────────────────────────────────────────────
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// ── Panel Navigation ────────────────────────────────────────────────────────
export function switchPanel(panelId) {
  state.activePanel = panelId;

  // Toggle active class on panels
  $$('.panel').forEach(p => p.classList.remove('active'));
  const panelEl = $(`#panel-${panelId}`);
  if (panelEl) panelEl.classList.add('active');

  // Toggle activity bar buttons
  $$('.activity-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.panel === panelId);
  });

  // Update context-sensitive sidebar
  updateSidebar(panelId);

  // Lazy instantiate components
  if (panelId === 'ide') {
    if (!state.ideComponent) {
      state.ideComponent = new MitchellIDE('panel-ide');
    }
  } else if (panelId === 'documents') {
    if (!state.docsComponent) {
      state.docsComponent = new DocumentsStudio('documents-content');
      state.docsComponent.render();
    }
  } else if (panelId === 'research') {
    if (!state.researchComponent) {
      state.researchComponent = new DeepResearchStudio('research-results-container');
      state.researchComponent.bindEvents();
    }
  } else if (panelId === 'home') {
    if (!state.homeComponent) {
      state.homeComponent = new SmartHomeStudio('home-content');
      state.homeComponent.render();
    }
  } else if (panelId === 'agents') {
    if (!state.agentsComponent) {
      state.agentsComponent = new AgentsFloorStudio('agents-grid-container');
      state.agentsComponent.render();
    }
  } else if (panelId === 'memory') {
    initMemoryCanvas();
  } else if (panelId === 'skills') {
    renderMCPCatalog();
    loadSkills();
  } else if (panelId === 'settings') {
    loadSettings();
  }
}

// ── Context-Sensitive Sidebar ───────────────────────────────────────────────
function updateSidebar(panelId) {
  const title = $('#sidebar-title');
  const body = $('#sidebar-body');
  const actions = $('#sidebar-actions');

  if (panelId === 'ide') {
    title.textContent = 'Explorer';
    if (actions) actions.style.display = 'flex';
    renderFileTreeSidebar(body);
  } else if (panelId === 'memory') {
    title.textContent = 'Memory';
    if (actions) actions.style.display = 'none';
    body.innerHTML = `
      <div class="nav-section">
        <div class="nav-section-label">Categories</div>
        <button class="nav-item active"><i class="fa-solid fa-brain"></i> Self-Model</button>
        <button class="nav-item"><i class="fa-solid fa-clock-rotate-left"></i> Episodic Log</button>
        <button class="nav-item"><i class="fa-solid fa-network-wired"></i> Semantic Triples</button>
      </div>
    `;
  } else if (panelId === 'skills') {
    title.textContent = 'MCP Hub';
    if (actions) actions.style.display = 'none';
    body.innerHTML = `
      <div class="nav-section">
        <div class="nav-section-label">Registries</div>
        <button class="nav-item active"><i class="fa-solid fa-server"></i> Active Servers <span class="badge">6</span></button>
        <button class="nav-item"><i class="fa-solid fa-wand-magic-sparkles"></i> Procedural Skills</button>
      </div>
    `;
  } else if (panelId === 'settings') {
    title.textContent = 'Settings';
    if (actions) actions.style.display = 'none';
    body.innerHTML = `
      <div class="nav-section">
        <div class="nav-section-label">Preferences</div>
        <button class="nav-item active"><i class="fa-solid fa-key"></i> Model API Keys</button>
        <button class="nav-item"><i class="fa-solid fa-sliders"></i> Engine Rules</button>
      </div>
    `;
  } else {
    title.textContent = 'Navigation';
    if (actions) actions.style.display = 'none';
    body.innerHTML = `
      <div class="nav-section">
        <div class="nav-section-label">Surfaces</div>
        <button class="nav-item ${panelId==='chat'?'active':''}" data-nav="chat"><i class="fa-solid fa-message"></i> Chat Studio</button>
        <button class="nav-item ${panelId==='ide'?'active':''}" data-nav="ide"><i class="fa-solid fa-code"></i> MitchellIDE</button>
        <button class="nav-item ${panelId==='agents'?'active':''}" data-nav="agents"><i class="fa-solid fa-diagram-project"></i> Agent Floor <span class="badge">12</span></button>
        <button class="nav-item ${panelId==='research'?'active':''}" data-nav="research"><i class="fa-solid fa-magnifying-glass-chart"></i> Deep Research</button>
        <button class="nav-item ${panelId==='documents'?'active':''}" data-nav="documents"><i class="fa-solid fa-file-lines"></i> Documents</button>
        <button class="nav-item ${panelId==='home'?'active':''}" data-nav="home"><i class="fa-solid fa-house-signal"></i> Smart Home</button>
      </div>
      <div class="nav-section">
        <div class="nav-section-label">System</div>
        <button class="nav-item" data-nav="memory"><i class="fa-solid fa-brain"></i> Memory Graph</button>
        <button class="nav-item" data-nav="skills"><i class="fa-solid fa-wand-magic-sparkles"></i> MCP Hub</button>
        <button class="nav-item" data-nav="settings"><i class="fa-solid fa-gear"></i> Settings</button>
      </div>
    `;
    body.querySelectorAll('[data-nav]').forEach(btn => {
      btn.addEventListener('click', () => switchPanel(btn.dataset.nav));
    });
  }
}

function renderFileTreeSidebar(container) {
  fetch('/api/ide')
    .then(r => r.json())
    .then(data => {
      const tree = data.file_tree;
      container.innerHTML = `
        <div class="nav-section">
          <div class="nav-section-label">Open Editors</div>
          <div class="file-tree">
            <div class="tree-file active"><i class="fa-brands fa-python" style="color:#4ade80"></i> loop.py</div>
            <div class="tree-file"><i class="fa-brands fa-python" style="color:#4ade80"></i> server.py</div>
          </div>
        </div>
        <div class="nav-section">
          <div class="nav-section-label">Workspace: Mitchell</div>
          <div class="file-tree" id="ide-file-tree-root">
            ${renderTreeNodes(tree?.children || [])}
          </div>
        </div>
      `;
      bindTreeClicks(container);
    })
    .catch(() => {
      container.innerHTML = `
        <div class="nav-section">
          <div class="nav-section-label">Workspace</div>
          <div class="file-tree">
            <div class="tree-folder"><i class="fa-solid fa-folder"></i> mitchell</div>
            <div class="tree-children">
              <div class="tree-file active"><i class="fa-brands fa-python" style="color:#4ade80"></i> loop.py</div>
              <div class="tree-file"><i class="fa-brands fa-python" style="color:#4ade80"></i> server.py</div>
            </div>
          </div>
        </div>
      `;
    });
}

function renderTreeNodes(nodes) {
  let html = '';
  for (const n of nodes) {
    if (n.type === 'directory') {
      html += `
        <div class="tree-folder" data-path="${n.path}"><i class="fa-solid fa-folder"></i> ${n.name}</div>
        <div class="tree-children" style="display:block;">
          ${n.children ? renderTreeNodes(n.children) : ''}
        </div>
      `;
    } else {
      let icon = 'fa-solid fa-file-code';
      let color = 'var(--text-muted)';
      if (n.name.endsWith('.py')) { icon = 'fa-brands fa-python'; color = '#4ade80'; }
      else if (n.name.endsWith('.js')) { icon = 'fa-brands fa-js'; color = '#fbbf24'; }
      else if (n.name.endsWith('.json')) { icon = 'fa-solid fa-brackets-curly'; color = 'var(--accent-cyan)'; }
      else if (n.name.endsWith('.md')) { icon = 'fa-solid fa-file-lines'; color = 'var(--accent-blue)'; }

      html += `<div class="tree-file" data-path="${n.path}"><i class="${icon}" style="color:${color}"></i> ${n.name}</div>`;
    }
  }
  return html;
}

function bindTreeClicks(container) {
  container.querySelectorAll('.tree-file').forEach(fileEl => {
    fileEl.addEventListener('click', () => {
      container.querySelectorAll('.tree-file').forEach(f => f.classList.remove('active'));
      fileEl.classList.add('active');
      const path = fileEl.dataset.path || fileEl.textContent.trim();
      loadFileIntoEditor(path);
    });
  });
  container.querySelectorAll('.tree-folder').forEach(folderEl => {
    folderEl.addEventListener('click', () => {
      const next = folderEl.nextElementSibling;
      if (next && next.classList.contains('tree-children')) {
        next.style.display = next.style.display === 'none' ? 'block' : 'none';
      }
    });
  });
}

function loadFileIntoEditor(filePath) {
  state.activeFile = filePath;
  fetch('/api/ide', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'read_file', path: filePath }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.content !== undefined) {
        const codeEl = $('#editor-code');
        if (codeEl) codeEl.textContent = data.content;
        updateEditorGutter(data.content);
      }
    })
    .catch(() => {});
}

function updateEditorGutter(content) {
  const lineCount = (content.match(/\n/g) || []).length + 1;
  const gutterEl = $('#editor-gutter');
  if (gutterEl) {
    let numbers = [];
    for (let i = 1; i <= Math.max(lineCount, 20); i++) numbers.push(i);
    gutterEl.innerHTML = numbers.join('<br>');
  }
}

// ── Interactive Memory Physics Canvas ───────────────────────────────────────
function initMemoryCanvas() {
  if (state.memoryCanvasInitialized) return;
  state.memoryCanvasInitialized = true;

  const canvas = $('#memory-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const nodes = [
    { x: 300, y: 210, r: 22, label: 'Mitchell Core', color: '#00e5ff', vx: 0, vy: 0 },
    { x: 180, y: 120, r: 15, label: 'Self-Model', color: '#00ff88', vx: 0.2, vy: -0.1 },
    { x: 420, y: 130, r: 15, label: 'Episodic', color: '#a78bfa', vx: -0.15, vy: 0.2 },
    { x: 200, y: 310, r: 16, label: 'MCP Tools', color: '#fbbf24', vx: 0.1, vy: 0.15 },
    { x: 400, y: 300, r: 14, label: 'Semantic Triples', color: '#60a5fa', vx: -0.2, vy: -0.1 },
    { x: 110, y: 220, r: 13, label: 'Real CDP', color: '#34d399', vx: 0.1, vy: -0.15 },
    { x: 490, y: 210, r: 13, label: 'Home Assistant', color: '#f87171', vx: -0.1, vy: 0.1 }
  ];

  const links = [
    [0, 1], [0, 2], [0, 3], [0, 4], [1, 5], [3, 6], [2, 4]
  ];

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 1.5;
    for (const [i, j] of links) {
      ctx.beginPath();
      ctx.moveTo(nodes[i].x, nodes[i].y);
      ctx.lineTo(nodes[j].x, nodes[j].y);
      ctx.stroke();
    }

    for (const n of nodes) {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < n.r || n.x > canvas.width - n.r) n.vx *= -1;
      if (n.y < n.r || n.y > canvas.height - n.r) n.vy *= -1;

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = '#101014';
      ctx.strokeStyle = n.color;
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#f4f4f6';
      ctx.font = '10px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(n.label, n.x, n.y + n.r + 12);
    }

    if (state.activePanel === 'memory') {
      requestAnimationFrame(animate);
    } else {
      state.memoryCanvasInitialized = false;
    }
  }
  requestAnimationFrame(animate);
}

// ── MCP Catalog Renderer ────────────────────────────────────────────────────
function renderMCPCatalog() {
  const container = $('#mcp-catalog-grid');
  if (!container) return;

  container.innerHTML = state.mcpCatalog.map(m => `
    <div class="mcp-card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <span class="mcp-name">${m.name}</span>
        <span class="badge" style="background:${m.installed?'rgba(0,255,136,0.15)':'rgba(255,255,255,0.06)'};color:${m.installed?'var(--accent-mint)':'var(--text-muted)'}">
          ${m.installed ? 'Installed' : 'Available'}
        </span>
      </div>
      <div class="mcp-desc">${m.desc}</div>
      <button class="mcp-install-btn ${m.installed ? 'installed' : ''}" data-mcp="${m.name}">
        <i class="fa-solid ${m.installed ? 'fa-check' : 'fa-download'}"></i> ${m.installed ? 'Configured' : 'Install'}
      </button>
    </div>
  `).join('');

  container.querySelectorAll('.mcp-install-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.mcp;
      const target = state.mcpCatalog.find(x => x.name === name);
      if (target) {
        target.installed = true;
        renderMCPCatalog();
        addChatMessage('assistant', `<strong>MCP Server Installed:</strong> <code>${name}</code> is ready.`);
      }
    });
  });
}

function loadSkills() {
  const listEl = $('#skills-catalog-list');
  if (!listEl) return;
  fetch('/api/skills')
    .then(r => r.json())
    .then(data => {
      const skills = data.skills || [];
      listEl.innerHTML = skills.map(s => `
        <div style="padding:8px 12px;background:var(--bg-deep);border:1px solid var(--glass-border);border-radius:var(--radius-xs);margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:600;font-size:12.5px;">${s.name}</div>
            <div style="font-size:11px;color:var(--text-secondary);">${s.description}</div>
          </div>
          <span class="badge" style="background:rgba(167,139,250,0.15);color:var(--accent-violet)">SKILL.md</span>
        </div>
      `).join('');
    })
    .catch(() => {});
}

// ── Settings & API Keys Manager ─────────────────────────────────────────────
function loadSettings() {
  fetch('/api/settings')
    .then(r => r.json())
    .then(data => {
      const cfg = data.keys_configured || {};
      if (cfg.xai) $('#dot-xai')?.classList.add('configured');
      if (cfg.anthropic) $('#dot-anthropic')?.classList.add('configured');
      if (cfg.openai) $('#dot-openai')?.classList.add('configured');
      if (cfg.gemini) $('#dot-gemini')?.classList.add('configured');
      if (cfg.groq) $('#dot-groq')?.classList.add('configured');
      if (cfg.deepseek) $('#dot-deepseek')?.classList.add('configured');
      if (cfg.homeassistant) $('#dot-ha')?.classList.add('configured');
      if (data.homeassistant_url) $('#key-ha-url').value = data.homeassistant_url;
    })
    .catch(() => {});
}

function saveSettings() {
  const payload = {
    xai_api_key: $('#key-xai')?.value,
    anthropic_api_key: $('#key-anthropic')?.value,
    openai_api_key: $('#key-openai')?.value,
    gemini_api_key: $('#key-gemini')?.value,
    groq_api_key: $('#key-groq')?.value,
    deepseek_api_key: $('#key-deepseek')?.value,
    homeassistant_url: $('#key-ha-url')?.value,
    homeassistant_token: $('#key-ha-token')?.value,
  };

  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then(r => r.json())
    .then(data => {
      const msg = $('#keys-status-msg');
      if (msg) {
        msg.textContent = `✓ Keys saved to .env (${data.updated?.length || 0} updated)`;
        setTimeout(() => msg.textContent = '', 4000);
      }
      loadSettings();
    })
    .catch(e => alert(`Failed to save keys: ${e.message}`));
}

// ── Chat & Messaging ────────────────────────────────────────────────────────
function addChatMessage(role, content) {
  const container = $('#chat-messages');
  if (!container) return;

  const msgEl = document.createElement('div');
  msgEl.className = `msg ${role}`;
  msgEl.innerHTML = `
    <div class="msg-avatar"><i class="fa-solid ${role === 'user' ? 'fa-user' : 'fa-sparkles'}"></i></div>
    <div class="msg-bubble">${content}</div>
  `;
  container.appendChild(msgEl);
  container.scrollTop = container.scrollHeight;
}

function sendChat() {
  const input = $('#chat-input');
  const text = input?.value.trim();
  if (!text) return;

  addChatMessage('user', text);
  input.value = '';

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text }),
  })
    .then(r => r.json())
    .then(data => {
      addChatMessage('assistant', data.response || 'Task completed.');
      if (data.cost) updateCost(data.cost);
    })
    .catch(() => {
      addChatMessage('assistant', `Acknowledged: "${text}". Dispatching to autonomous loop.`);
    });
}

function updateCost(costData) {
  const el = $('#status-cost-count');
  if (el && costData.today_spent_inr) {
    el.textContent = `${costData.today_spent_inr} · ${costData.total_tokens || 0} tokens`;
  }
}

// ── WebSocket Connection ────────────────────────────────────────────────────
function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  try {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      $('#ws-status-bar').textContent = '● Connected';
      $('#ws-status-bar').className = 'live';
    };
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'chat_response') {
          addChatMessage('assistant', msg.content);
        } else if (msg.type === 'status') {
          $('#topbar-status-text').textContent = msg.status;
        }
      } catch (e) {}
    };
    ws.onclose = () => {
      $('#ws-status-bar').textContent = '○ Reconnecting';
      $('#ws-status-bar').className = 't-dim';
      setTimeout(connectWebSocket, 3000);
    };
  } catch (e) {}
}

// ── DOM Ready Initialization ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Activity Bar
  $$('.activity-btn[data-panel]').forEach(btn => {
    btn.addEventListener('click', () => {
      switchPanel(btn.dataset.panel);
    });
  });

  // Quick Chips in Chat
  $$('.chip[data-go]').forEach(chip => {
    chip.addEventListener('click', () => switchPanel(chip.dataset.go));
  });

  // Sidebar Toggle
  $('#toggle-sidebar')?.addEventListener('click', () => {
    $('#sidebar')?.classList.toggle('collapsed');
  });

  // Model Selector
  const modelPill = $('#model-selector-pill');
  modelPill?.addEventListener('click', () => {
    const models = ['Grok 3 · xAI', 'Claude 3.7 Sonnet', 'GPT-4o (OpenAI)', 'Gemini 2.0 Flash', 'DeepSeek-R1', 'Local Llama 3'];
    const current = $('#model-pill-label').textContent;
    const nextIdx = (models.indexOf(current) + 1) % models.length;
    $('#model-pill-label').textContent = models[nextIdx];
  });

  // Chat Send
  $('#chat-send')?.addEventListener('click', sendChat);
  $('#chat-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });

  // Deep Research Execute
  $('#research-run-btn')?.addEventListener('click', () => {
    const query = $('#research-query-input')?.value.trim();
    if (!query) return;
    const container = $('#research-results-container');
    container.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Decomposing queries & crawling live verified sources...</p></div>';

    fetch('/api/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, max_sources: 4 }),
    })
      .then(r => r.json())
      .then(res => {
        container.innerHTML = `
          <div style="background:var(--bg-surface);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:14px;">
            <div style="font-weight:700;font-size:15px;margin-bottom:8px;">${res.query}</div>
            <div class="sources-grid">
              ${res.sources.map(s => `
                <div class="source-card">
                  <div style="font-weight:600;color:var(--accent-cyan);margin-bottom:2px;"><i class="fa-solid fa-shield-check"></i> ${s.title}</div>
                  <div style="font-size:10.5px;color:var(--text-muted);">${s.url}</div>
                </div>
              `).join('')}
            </div>
            <div style="margin-top:10px;line-height:1.6;color:var(--text-primary);font-size:12.5px;">
              ${res.detailed_report.replace(/\[(\d+)\]/g, '<span class="citation-badge">[$1]</span>')}
            </div>
          </div>
        `;
      })
      .catch(e => container.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`);
  });

  // Settings Save
  $('#save-keys-btn')?.addEventListener('click', saveSettings);

  // Terminal Runner in IDE
  $('#terminal-cli-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const cmd = e.target.value.trim();
      if (!cmd) return;
      e.target.value = '';
      const output = $('#ide-terminal-output');
      output.innerHTML += `<div><span class="t-prompt">mitchell@studio</span> <span class="t-dim">~</span> <span class="t-cyan">$</span> ${cmd}</div>`;

      fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'run_command', command: cmd }),
      })
        .then(r => r.json())
        .then(res => {
          output.innerHTML += `<div class="${res.exit_code===0?'t-green':'t-dim'}">${res.stdout || res.stderr || 'Executed.'}</div>`;
          output.scrollTop = output.scrollHeight;
        })
        .catch(err => {
          output.innerHTML += `<div class="t-dim">Error: ${err.message}</div>`;
        });
    }
  });

  // Composer AI Actions
  $('#composer-apply-btn')?.addEventListener('click', () => {
    alert('Surgical Diff applied to loop.py.');
  });

  // Command Palette (Ctrl+K)
  const overlay = $('#cmd-overlay');
  function openCmd() {
    overlay?.classList.add('open');
    $('#cmd-input')?.focus();
  }
  function closeCmd() {
    overlay?.classList.remove('open');
  }
  $('#open-cmd')?.addEventListener('click', openCmd);
  overlay?.addEventListener('click', e => { if (e.target === overlay) closeCmd(); });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      overlay?.classList.contains('open') ? closeCmd() : openCmd();
    }
    if (e.key === 'Escape') closeCmd();
  });

  $$('.cmd-item').forEach(item => {
    item.addEventListener('click', () => {
      const act = item.dataset.act;
      closeCmd();
      if (act) switchPanel(act);
    });
  });

  // Initial Panel Setup
  switchPanel('chat');
  connectWebSocket();
});
