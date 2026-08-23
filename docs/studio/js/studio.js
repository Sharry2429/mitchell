/**
 * Mitchell Studio — Command-Driven Autonomous Workspace Master Controller
 * Chat is the Home. Everything else is summoned.
 */

import { MitchellIDE } from './components/ide.js';
import { DeepResearchStudio } from './components/research.js';
import { SkillsMCPStudio } from './components/skills_mcp.js';
import { ProjectsStudio } from './components/projects.js';
import { ResourceWatchStudio } from './components/resource_watch.js';
import { DevicesStudio } from './components/iot.js';
import { FileExplorerStudio } from './components/file_explorer.js';

class MitchellStudioController {
  constructor() {
    this.activePanel = 'chat';
    this.activeModel = 'grok-3-mini';
    this.activeTheme = 'grok';
    this.ws = null;
    this.sessions = [];
    this.currentSessionId = null;
    this.attachedFiles = [];
    this.isRecordingVoice = false;
    this.recognition = null;

    // Component instances
    this.ideComponent = null;
    this.researchComponent = null;
    this.skillsComponent = null;
    this.projectsComponent = null;
    this.resourceWatch = new ResourceWatchStudio('resource-hud-overlay');
    this.devicesComponent = null;
    this.filesComponent = null;
  }

  async init() {
    this.loadSessionsFromStorage();
    this.bindGlobalEvents();
    this.initWebSocket();
    this.initVoiceSTT();
    this.renderHistorySidebar();

    // Start with a new or most recent session
    if (this.sessions.length > 0) {
      this.loadSession(this.sessions[0].id);
    } else {
      this.createNewSession();
    }

    // Expose controller globally
    window.__mitchellStudioController = this;
  }

  // ── Layout Navigation & Dynamic Summoning ──────────────────────────────────
  activatePanel(panelId, initialData = null) {
    this.activePanel = panelId;

    // Toggle active panel DOM
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const target = document.getElementById(`panel-${panelId}`);
    if (target) target.classList.add('active');

    // Lazy instantiate components
    if (panelId === 'ide') {
      if (!this.ideComponent) {
        this.ideComponent = new MitchellIDE('ide-container');
        this.ideComponent.render();
      }
      if (initialData && initialData.file) {
        this.ideComponent.openFile(initialData.file);
      }
    } else if (panelId === 'research') {
      if (!this.researchComponent) {
        this.researchComponent = new DeepResearchStudio('research-container');
      }
      this.researchComponent.render(initialData?.query || '');
    } else if (panelId === 'skills') {
      if (!this.skillsComponent) {
        this.skillsComponent = new SkillsMCPStudio('skills-container');
      }
      this.skillsComponent.render();
      if (initialData?.package) {
        this.skillsComponent.installMCP(initialData.package);
      }
    } else if (panelId === 'projects') {
      if (!this.projectsComponent) {
        this.projectsComponent = new ProjectsStudio('projects-container');
      }
      this.projectsComponent.render();
    } else if (panelId === 'devices') {
      if (!this.devicesComponent) {
        this.devicesComponent = new DevicesStudio('devices-container');
      }
      this.devicesComponent.render();
    } else if (panelId === 'files') {
      if (!this.filesComponent) {
        this.filesComponent = new FileExplorerStudio('file-explorer-container');
      }
      this.filesComponent.render();
      if (initialData?.query) {
        this.filesComponent.searchFiles(initialData.query);
      }
    } else if (panelId === 'settings') {
      this.loadSettings();
    }
  }

  // ── Natural Language Command Router ───────────────────────────────────────
  parseAndExecuteCommand(text) {
    const raw = text.trim();
    const lower = raw.toLowerCase();

    // 1. Open IDE
    if (lower === 'open ide' || lower === 'mitchell open ide' || lower === 'launch ide' || lower === 'ide') {
      this.activatePanel('ide');
      return {
        handled: true,
        response: 'Opening IDE Mode with Monaco editor, workspace file tree, and interactive terminal.'
      };
    }

    // 2. Open Researcher / Deep Research
    if (lower.startsWith('open researcher') || lower.startsWith('deep research') || lower.startsWith('research ')) {
      const q = raw.replace(/open researcher/i, '').replace(/deep research/i, '').replace(/research/i, '').replace(/^[:\s-]+/, '');
      this.activatePanel('research', { query: q });
      return {
        handled: true,
        response: q ? `Summoning Deep Researcher for: "${q}"...` : 'Summoning Deep Researcher...'
      };
    }

    // 3. Show Resources / Resource Watch HUD
    if (lower.includes('show resources') || lower.includes('resource watch') || lower.includes('system resources') || lower === 'resources') {
      this.resourceWatch.show();
      return {
        handled: true,
        response: 'Displaying floating Resource Watch HUD overlay with live CPU, RAM, Disk, and Battery telemetry.'
      };
    }

    // 4. Pair Android / Wireless Debugging / Sync Devices
    if (lower.includes('pair android') || lower.includes('wireless debugging') || lower.includes('wireless adb') || lower.includes('sync device') || lower.includes('sync phone') || lower.includes('connect phone')) {
      fetch('/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'pair_android', port: 5555 }),
      }).then(r => r.json()).then(data => {
        if (this.devicesComponent) this.devicesComponent.loadData();
      });
      this.activatePanel('devices');
      return {
        handled: true,
        response: '⚡ **Android Wireless Pairing Sequence Initiated**\n1. Detecting USB connected phone...\n2. Enabling TCP/IP port `5555` on local Wi-Fi network...\n3. Establishing Wireless ADB connection...\n\n*Summoning Devices Console... You can unplug the USB cable once paired!*'
      };
    }

    // 5. Show Devices Console
    if (lower.includes('show devices') || lower.includes('open devices') || lower === 'devices') {
      this.activatePanel('devices');
      return {
        handled: true,
        response: 'Opening Devices Console (Android companion, Windows workstation, Home Assistant IoT).'
      };
    }

    // 6. Open Project
    if (lower.startsWith('open project')) {
      const pName = raw.replace(/open project/i, '').trim();
      this.activatePanel('projects');
      return {
        handled: true,
        response: `Opening Isolated Projects workspace${pName ? ` (target: ${pName})` : ''}...`
      };
    }

    // 6. Install MCP
    if (lower.includes('install @') || lower.includes('install mcp')) {
      const pkg = raw.split(/install/i).pop().trim();
      this.activatePanel('skills', { package: pkg });
      return {
        handled: true,
        response: `Installing live Model Context Protocol server: \`${pkg}\`...`
      };
    }

    // 7. Spawn Dynamic Agent (Hermes Swarm)
    if (lower.startsWith('spawn agent') || lower.startsWith('create agent') || lower.startsWith('spawn dynamic agent')) {
      const aName = raw.replace(/spawn dynamic agent|spawn agent|create agent/i, '').trim() || 'CustomWorker';
      fetch('/api/agents/dynamic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'spawn', name: aName, description: `Autonomous subagent '${aName}'`, model: this.activeModel }),
      }).then(() => {
        if (this.skillsComponent) this.skillsComponent.loadData();
      });
      this.activatePanel('skills');
      return {
        handled: true,
        response: `Spawning dynamic Hermes autonomous subagent: \`${aName}\` with full tool execution & ReAct loop!`
      };
    }

    // 8. Create / Install Skill
    if (lower.startsWith('create skill') || lower.startsWith('install skill')) {
      const sName = raw.replace(/create skill|install skill/i, '').trim() || 'custom_skill';
      fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', name: sName, description: `Procedural skill ${sName}` }),
      }).then(() => {
        if (this.skillsComponent) this.skillsComponent.loadData();
      });
      this.activatePanel('skills');
      return {
        handled: true,
        response: `Registering procedural skill \`${sName}\` in Skill Library...`
      };
    }

    // 9. Find Document / Files
    if (lower.includes('find document') || lower.includes('find file') || lower.includes('search file')) {
      const q = raw.split(/contains|that|for/i).pop().trim();
      this.activatePanel('files', { query: q });
      return {
        handled: true,
        response: `Searching workspace documents containing "${q}"...`
      };
    }

    // 10. Open API Keys / .env
    if ((lower.includes('api keys') || lower.includes('.env')) && lower.includes('file')) {
      this.activatePanel('ide', { file: '.env' });
      return {
        handled: true,
        response: 'Opening `.env` in the Monaco editor.'
      };
    }

    return { handled: false };
  }

  // ── Chat Messaging Engine ──────────────────────────────────────────────────
  async sendMessage(promptText = '') {
    const input = document.getElementById('chat-prompt-input');
    const text = promptText || input?.value.trim();
    if (!text && this.attachedFiles.length === 0) return;

    if (input) input.value = '';

    // Hide hero on first message
    const hero = document.getElementById('chat-hero');
    if (hero) hero.style.display = 'none';

    // Append User message
    const userMsg = {
      role: 'user',
      content: text,
      files: [...this.attachedFiles],
      timestamp: new Date().toISOString(),
    };
    this.appendMessageToStream(userMsg);
    this.attachedFiles = [];
    this.renderAttachedChips();

    // Check client-side command parsing
    const cmdResult = this.parseAndExecuteCommand(text);
    if (cmdResult.handled) {
      this.appendMessageToStream({
        role: 'assistant',
        content: cmdResult.response,
        timestamp: new Date().toISOString(),
      });
      this.saveActiveSession();
      return;
    }

    // Show Thinking indicator
    const stream = document.getElementById('chat-messages-stream');
    const thinkingElem = document.createElement('div');
    thinkingElem.className = 'chat-bubble-wrap assistant';
    thinkingElem.id = 'thinking-indicator';
    thinkingElem.innerHTML = `
      <div class="chat-avatar"><i class="fa-solid fa-sparkles"></i></div>
      <div class="chat-bubble" style="color:var(--accent-cyan);font-family:var(--font-mono);font-size:12px;">
        <i class="fa-solid fa-spinner fa-spin"></i> Mitchell thinking (${this.activeModel})...
      </div>
    `;
    stream?.appendChild(thinkingElem);
    stream.scrollTop = stream.scrollHeight;

    // Send to backend
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          model: this.activeModel,
          session_id: this.currentSessionId,
        }),
      });
      const data = await resp.json();
      thinkingElem.remove();

      const assistantMsg = {
        role: 'assistant',
        content: data.response || 'No response returned.',
        duration: data.duration,
        command_intent: data.command_intent,
        timestamp: new Date().toISOString(),
      };
      this.appendMessageToStream(assistantMsg);

      // If backend detected a command intent, execute layout switch
      if (data.command_intent) {
        if (data.command_intent.action === 'open_ide') this.activatePanel('ide');
        else if (data.command_intent.action === 'open_researcher') this.activatePanel('research', { query: data.command_intent.query });
        else if (data.command_intent.action === 'show_resources') this.resourceWatch.show();
        else if (data.command_intent.action === 'show_devices') this.activatePanel('devices');
      }

      this.saveActiveSession();
    } catch (e) {
      thinkingElem.remove();
      this.appendMessageToStream({
        role: 'assistant',
        content: `Error contacting Mitchell Hive: ${e.message}`,
        timestamp: new Date().toISOString(),
      });
    }
  }

  appendMessageToStream(msg) {
    const stream = document.getElementById('chat-messages-stream');
    if (!stream) return;

    const wrap = document.createElement('div');
    wrap.className = `chat-bubble-wrap ${msg.role}`;

    const icon = msg.role === 'user' ? 'fa-user' : 'fa-sparkles';
    let contentHtml = this.formatMarkdown(msg.content);

    if (msg.files && msg.files.length > 0) {
      contentHtml = `<div style="display:flex;gap:4px;margin-bottom:6px;">${msg.files.map(f => `<span class="attached-chip"><i class="fa-solid fa-file"></i> ${f}</span>`).join('')}</div>` + contentHtml;
    }

    wrap.innerHTML = `
      <div class="chat-avatar"><i class="fa-solid ${icon}"></i></div>
      <div class="chat-bubble">${contentHtml}</div>
    `;

    stream.appendChild(wrap);
    stream.scrollTop = stream.scrollHeight;

    // Track in active session
    const session = this.getActiveSession();
    if (session) {
      session.messages.push(msg);
      if (session.messages.length === 1 && msg.role === 'user') {
        session.title = msg.content.slice(0, 32) + (msg.content.length > 32 ? '...' : '');
        this.renderHistorySidebar();
      }
    }
  }

  formatMarkdown(text) {
    if (!text) return '';
    let formatted = text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
    return formatted;
  }

  // ── Session History Persistence ───────────────────────────────────────────
  loadSessionsFromStorage() {
    try {
      const data = localStorage.getItem('mitchell_chat_sessions');
      this.sessions = data ? JSON.parse(data) : [];
    } catch (e) {
      this.sessions = [];
    }
  }

  saveActiveSession() {
    try {
      localStorage.setItem('mitchell_chat_sessions', JSON.stringify(this.sessions));
    } catch (e) {}
  }

  createNewSession() {
    const session = {
      id: 'sess_' + Date.now(),
      title: 'New Conversation',
      created_at: new Date().toISOString(),
      messages: [],
    };
    this.sessions.unshift(session);
    this.currentSessionId = session.id;
    this.saveActiveSession();
    this.renderHistorySidebar();
    this.renderActiveSessionMessages();
    this.activatePanel('chat');

    // Show hero
    const hero = document.getElementById('chat-hero');
    if (hero) hero.style.display = 'flex';
  }

  loadSession(sessionId) {
    this.currentSessionId = sessionId;
    this.renderHistorySidebar();
    this.renderActiveSessionMessages();
    this.activatePanel('chat');
  }

  deleteSession(sessionId, e) {
    if (e) e.stopPropagation();
    this.sessions = this.sessions.filter(s => s.id !== sessionId);
    this.saveActiveSession();
    if (this.currentSessionId === sessionId) {
      if (this.sessions.length > 0) this.loadSession(this.sessions[0].id);
      else this.createNewSession();
    } else {
      this.renderHistorySidebar();
    }
  }

  getActiveSession() {
    return this.sessions.find(s => s.id === this.currentSessionId);
  }

  renderActiveSessionMessages() {
    const stream = document.getElementById('chat-messages-stream');
    const hero = document.getElementById('chat-hero');
    if (!stream) return;

    stream.innerHTML = '';
    const session = this.getActiveSession();

    if (session && session.messages.length > 0) {
      if (hero) hero.style.display = 'none';
      session.messages.forEach(m => {
        const wrap = document.createElement('div');
        wrap.className = `chat-bubble-wrap ${m.role}`;
        const icon = m.role === 'user' ? 'fa-user' : 'fa-sparkles';
        wrap.innerHTML = `
          <div class="chat-avatar"><i class="fa-solid ${icon}"></i></div>
          <div class="chat-bubble">${this.formatMarkdown(m.content)}</div>
        `;
        stream.appendChild(wrap);
      });
      stream.scrollTop = stream.scrollHeight;
    } else {
      if (hero) hero.style.display = 'flex';
    }
  }

  renderHistorySidebar() {
    const todayGroup = document.getElementById('history-group-today');
    const yesterdayGroup = document.getElementById('history-group-yesterday');
    const weekGroup = document.getElementById('history-group-week');

    if (!todayGroup || !yesterdayGroup || !weekGroup) return;

    todayGroup.innerHTML = '';
    yesterdayGroup.innerHTML = '';
    weekGroup.innerHTML = '';

    const now = new Date();
    const oneDay = 24 * 60 * 60 * 1000;

    this.sessions.forEach(sess => {
      const sessDate = new Date(sess.created_at || Date.now());
      const diff = now - sessDate;

      const item = document.createElement('div');
      item.className = `history-item ${sess.id === this.currentSessionId ? 'active' : ''}`;
      item.innerHTML = `
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;"><i class="fa-regular fa-message" style="margin-right:6px;font-size:11px;"></i>${sess.title || 'Conversation'}</span>
        <button class="history-item-del" title="Delete"><i class="fa-solid fa-trash"></i></button>
      `;

      item.addEventListener('click', () => this.loadSession(sess.id));
      item.querySelector('.history-item-del')?.addEventListener('click', (e) => this.deleteSession(sess.id, e));

      if (diff < oneDay) {
        todayGroup.appendChild(item);
      } else if (diff < 2 * oneDay) {
        yesterdayGroup.appendChild(item);
      } else {
        weekGroup.appendChild(item);
      }
    });
  }

  // ── Voice Dictation (Web Speech API) ──────────────────────────────────────
  initVoiceSTT() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById('chat-prompt-input');
        if (input) {
          input.value = (input.value ? input.value + ' ' : '') + transcript;
        }
        this.stopVoice();
      };

      this.recognition.onerror = () => this.stopVoice();
      this.recognition.onend = () => this.stopVoice();
    }
  }

  toggleVoice() {
    if (!this.recognition) {
      window.alert('Speech recognition is not supported in this browser. Please use Chrome/Edge or type your command.');
      return;
    }
    if (this.isRecordingVoice) {
      this.stopVoice();
    } else {
      this.startVoice();
    }
  }

  startVoice() {
    if (!this.recognition) return;
    this.isRecordingVoice = true;
    const btn = document.getElementById('chat-voice-btn');
    if (btn) btn.classList.add('recording');
    try {
      this.recognition.start();
    } catch (e) {}
  }

  stopVoice() {
    this.isRecordingVoice = false;
    const btn = document.getElementById('chat-voice-btn');
    if (btn) btn.classList.remove('recording');
    try {
      this.recognition?.stop();
    } catch (e) {}
  }

  // ── WebSocket Real-Time Stream ─────────────────────────────────────────────
  initWebSocket() {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = () => {
        const dot = document.getElementById('ws-status-dot');
        const lbl = document.getElementById('ws-status-label');
        if (dot) dot.className = 'status-indicator online';
        if (lbl) lbl.textContent = 'Connected to Hive';
      };
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'cost' && data.cost) {
            const costElem = document.getElementById('status-cost-summary');
            if (costElem) costElem.textContent = `${data.cost.currency || '₹'}${data.cost.total_cost || '0.00'} · ${data.cost.total_tokens || 0} tokens`;
          } else if (data.type === 'mcp_installed' || data.type === 'mcp_removed' || data.type === 'skill_installed' || data.type === 'agent_spawned' || data.type === 'agent_destroyed') {
            // Real-time hot update with zero page refresh!
            if (this.skillsComponent) {
              this.skillsComponent.loadData();
            }
          }
        } catch (e) {}
      };
      this.ws.onclose = () => {
        const dot = document.getElementById('ws-status-dot');
        const lbl = document.getElementById('ws-status-label');
        if (dot) dot.className = 'status-indicator';
        if (lbl) lbl.textContent = 'Offline';
        setTimeout(() => this.initWebSocket(), 5000);
      };
    } catch (e) {
      console.warn('WebSocket init fallback to REST API');
    }
  }

  // ── Settings Management ───────────────────────────────────────────────────
  async loadSettings() {
    try {
      const resp = await fetch('/api/settings');
      const data = await resp.json();
      const keys = data.keys_configured || {};
      ['anthropic', 'openai', 'xai', 'gemini', 'groq', 'deepseek'].forEach(k => {
        const dot = document.getElementById(`dot-${k}`);
        if (dot) dot.className = `key-indicator ${keys[k] ? 'active' : ''}`;
      });
      if (data.homeassistant_url) {
        const haInput = document.getElementById('key-ha-url');
        if (haInput) haInput.value = data.homeassistant_url;
      }
    } catch (e) {}
  }

  async saveSettings() {
    const payload = {};
    const map = {
      'key-anthropic': 'anthropic_api_key',
      'key-openai': 'openai_api_key',
      'key-xai': 'xai_api_key',
      'key-gemini': 'gemini_api_key',
      'key-groq': 'groq_api_key',
      'key-deepseek': 'deepseek_api_key',
      'key-ha-url': 'homeassistant_url',
      'key-ha-token': 'homeassistant_token',
    };

    for (const [elemId, field] of Object.entries(map)) {
      const val = document.getElementById(elemId)?.value.trim();
      if (val) payload[field] = val;
    }

    const statusBadge = document.getElementById('save-keys-status');
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (statusBadge) {
        statusBadge.textContent = 'Saved to .env!';
        setTimeout(() => statusBadge.textContent = '', 3000);
      }
      this.loadSettings();
    } catch (e) {
      if (statusBadge) statusBadge.textContent = 'Save error: ' + e.message;
    }
  }

  // ── Global Event Bindings ─────────────────────────────────────────────────
  bindGlobalEvents() {
    // Brand Home button
    document.getElementById('brand-home-btn')?.addEventListener('click', () => this.activatePanel('chat'));

    // Toggle Sidebar
    document.getElementById('toggle-history-btn')?.addEventListener('click', () => {
      const sb = document.getElementById('history-sidebar');
      sb?.classList.toggle('collapsed');
    });

    // New Chat
    document.getElementById('new-chat-btn')?.addEventListener('click', () => this.createNewSession());

    // Prompt Send
    document.getElementById('chat-send-btn')?.addEventListener('click', () => this.sendMessage());
    const promptInput = document.getElementById('chat-prompt-input');
    promptInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Voice Dictation
    document.getElementById('chat-voice-btn')?.addEventListener('click', () => this.toggleVoice());

    // Attachment
    const fileInput = document.getElementById('chat-file-input');
    const attachBtn = document.getElementById('chat-attach-btn');
    attachBtn?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', (e) => {
      const files = Array.from(e.target.files || []);
      files.forEach(f => this.attachedFiles.push(f.name));
      this.renderAttachedChips();
    });

    // Hero quick command chips
    document.querySelectorAll('.chip-cmd').forEach(chip => {
      chip.addEventListener('click', () => {
        const cmd = chip.dataset.cmd;
        if (cmd) this.sendMessage(cmd);
      });
    });

    // Titlebar Quick Summons
    document.getElementById('summon-ide-btn')?.addEventListener('click', () => this.activatePanel('ide'));
    document.getElementById('summon-researcher-btn')?.addEventListener('click', () => this.activatePanel('research'));
    document.getElementById('summon-resources-btn')?.addEventListener('click', () => this.resourceWatch.toggle());

    // Sidebar footer nav
    document.getElementById('nav-projects-btn')?.addEventListener('click', () => this.activatePanel('projects'));
    document.getElementById('nav-skills-btn')?.addEventListener('click', () => this.activatePanel('skills'));
    document.getElementById('nav-files-btn')?.addEventListener('click', () => this.activatePanel('files'));
    document.getElementById('nav-devices-btn')?.addEventListener('click', () => this.activatePanel('devices'));
    document.getElementById('nav-settings-btn')?.addEventListener('click', () => this.activatePanel('settings'));

    // Model dropdown
    const modelBtn = document.getElementById('model-selector-btn');
    const modelMenu = document.getElementById('model-dropdown-menu');
    modelBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      modelMenu?.classList.toggle('open');
    });
    document.querySelectorAll('.model-menu-item').forEach(item => {
      item.addEventListener('click', () => {
        const m = item.dataset.model;
        this.activeModel = m;
        document.querySelectorAll('.model-menu-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        const lbl = document.getElementById('current-model-label');
        if (lbl) lbl.textContent = item.querySelector('.model-item-title')?.textContent || m;
        modelMenu?.classList.remove('open');
      });
    });
    window.addEventListener('click', () => modelMenu?.classList.remove('open'));

    // Command Palette (Ctrl+K / Cmd+K)
    const cmdBackdrop = document.getElementById('cmd-palette-backdrop');
    const cmdInput = document.getElementById('cmd-palette-input');
    const openCmd = document.getElementById('open-cmd-palette');

    const showCmdPalette = () => {
      if (cmdBackdrop) cmdBackdrop.style.display = 'flex';
      if (cmdInput) {
        cmdInput.value = '';
        cmdInput.focus();
      }
    };
    const hideCmdPalette = () => {
      if (cmdBackdrop) cmdBackdrop.style.display = 'none';
    };

    openCmd?.addEventListener('click', showCmdPalette);
    cmdBackdrop?.addEventListener('click', (e) => {
      if (e.target === cmdBackdrop) hideCmdPalette();
    });

    document.querySelectorAll('.cmd-entry').forEach(entry => {
      entry.addEventListener('click', () => {
        const act = entry.dataset.action;
        hideCmdPalette();
        if (act === 'resources') this.resourceWatch.show();
        else this.activatePanel(act);
      });
    });

    cmdInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hideCmdPalette();
      else if (e.key === 'Enter') {
        const val = cmdInput.value.trim();
        hideCmdPalette();
        if (val) this.sendMessage(val);
      }
    });

    // Window Controls
    document.getElementById('win-min-btn')?.addEventListener('click', () => {
      const sb = document.getElementById('history-sidebar');
      sb?.classList.toggle('collapsed');
    });
    document.getElementById('win-max-btn')?.addEventListener('click', () => {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
      else document.exitFullscreen().catch(() => {});
    });
    document.getElementById('win-close-btn')?.addEventListener('click', () => {
      this.activatePanel('chat');
    });

    // Global Key Shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        showCmdPalette();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        document.getElementById('history-sidebar')?.classList.toggle('collapsed');
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        this.resourceWatch.toggle();
      } else if ((e.ctrlKey || e.metaKey) && e.key === '1') {
        e.preventDefault();
        this.activatePanel('chat');
      } else if ((e.ctrlKey || e.metaKey) && e.key === '2') {
        e.preventDefault();
        this.activatePanel('ide');
      } else if ((e.ctrlKey || e.metaKey) && e.key === '3') {
        e.preventDefault();
        this.activatePanel('research');
      }
    });

    // Settings save
    document.getElementById('save-settings-keys-btn')?.addEventListener('click', () => this.saveSettings());
  }

  renderAttachedChips() {
    const bar = document.getElementById('attached-files-bar');
    if (!bar) return;
    if (this.attachedFiles.length === 0) {
      bar.style.display = 'none';
      bar.innerHTML = '';
      return;
    }
    bar.style.display = 'flex';
    bar.innerHTML = this.attachedFiles.map((name, i) => `
      <div class="attached-chip">
        <i class="fa-solid fa-file"></i> <span>${name}</span>
        <span class="remove-file" onclick="window.__removeChatFile(${i})">×</span>
      </div>
    `).join('');
    window.__removeChatFile = (idx) => {
      this.attachedFiles.splice(idx, 1);
      this.renderAttachedChips();
    };
  }
}

// Instantiate on DOM load
document.addEventListener('DOMContentLoaded', () => {
  const app = new MitchellStudioController();
  app.init();
});
