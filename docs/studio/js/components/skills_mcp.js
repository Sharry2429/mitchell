/**
 * SkillsMCPStudio — Nous Hermes Dynamic Swarm, Skills & Real-Time MCP Hub
 * Features:
 * - Segmented tabs: Dynamic Swarm (Agents) | Custom MCPs | Procedural Skills | Connectors
 * - Real-time zero-refresh hot updates via WebSocket
 * - Live MCP installer: "Mitchell install @modelcontextprotocol/server-postgres"
 * - Dynamic Hermes subagent spawn & delegation modal
 * - Dynamic procedural SKILL.md creation & runner
 */

export class SkillsMCPStudio {
  constructor(containerId = 'skills-container') {
    this.container = document.getElementById(containerId);
    this.activeTab = 'agents'; // 'agents' | 'mcp' | 'skills' | 'connectors'
    this.mcpServers = [];
    this.skills = [];
    this.dynamicAgents = [];
    this.staticAgents = [];
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="skills-container" style="max-width:1100px;margin:0 auto;padding:20px 24px;overflow-y:auto;height:100%;">
        <!-- Tab Bar -->
        <div class="segmented-tabs" style="margin-bottom:18px;">
          <button class="segmented-tab-btn ${this.activeTab === 'agents' ? 'active' : ''}" data-tab="agents">
            <i class="fa-solid fa-network-wired" style="color:var(--accent-mint)"></i> Dynamic Swarm (${this.dynamicAgents.length + this.staticAgents.length})
          </button>
          <button class="segmented-tab-btn ${this.activeTab === 'mcp' ? 'active' : ''}" data-tab="mcp">
            <i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent-cyan)"></i> Real-Time MCP Hub (${this.mcpServers.length})
          </button>
          <button class="segmented-tab-btn ${this.activeTab === 'skills' ? 'active' : ''}" data-tab="skills">
            <i class="fa-solid fa-scroll" style="color:var(--accent-violet)"></i> Procedural Skills (${this.skills.length})
          </button>
          <button class="segmented-tab-btn ${this.activeTab === 'connectors' ? 'active' : ''}" data-tab="connectors">
            <i class="fa-solid fa-plug" style="color:var(--accent-amber)"></i> Connectors & Bridges
          </button>
        </div>

        <!-- Live Quick Action Bar (Context-dependent) -->
        <div id="skills-action-bar" style="margin-bottom:18px;">
          <!-- Populated by tab -->
        </div>

        <div id="mcp-install-status" style="margin:-10px 0 14px;font-size:11.5px;font-family:var(--font-mono);"></div>

        <!-- Tab Body Content -->
        <div id="skills-tab-content">
          <!-- Dynamically populated per tab -->
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    document.querySelectorAll('.segmented-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.segmented-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.activeTab = btn.dataset.tab;
        this.renderTabContent();
      });
    });
  }

  async loadData() {
    try {
      const [mcpResp, skillsResp, agentsResp, dynamicResp] = await Promise.all([
        fetch('/api/mcp'),
        fetch('/api/skills'),
        fetch('/api/agents'),
        fetch('/api/agents/dynamic'),
      ]);

      const mcpData = await mcpResp.json();
      const skillsData = await skillsResp.json();
      const agentsData = await agentsResp.json();
      const dynamicData = await dynamicResp.json();

      this.mcpServers = mcpData.servers || [];
      this.skills = skillsData.skills || [];
      this.staticAgents = agentsData.agents || [];
      this.dynamicAgents = dynamicData.dynamic_agents || [];

      this.renderTabContent();
    } catch (e) {
      console.warn('Data load error:', e);
      this.renderTabContent();
    }
  }

  renderTabContent() {
    const container = document.getElementById('skills-tab-content');
    const actionBar = document.getElementById('skills-action-bar');
    if (!container || !actionBar) return;

    if (this.activeTab === 'agents') {
      actionBar.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;background:var(--bg-surface);border:1px solid var(--glass-border);border-radius:var(--radius-lg);padding:10px 16px;">
          <div>
            <div style="font-weight:700;font-size:13px;color:var(--accent-mint);"><i class="fa-solid fa-robot"></i> Hermes Dynamic Multi-Agent Swarm</div>
            <div style="font-size:11.5px;color:var(--text-secondary);">Unlimited, non-fixed autonomous subagents with independent ReAct reasoning, memory & scoped tools.</div>
          </div>
          <button class="btn btn-primary btn-sm" id="btn-spawn-agent-modal"><i class="fa-solid fa-plus"></i> Spawn Dynamic Agent</button>
        </div>
      `;

      document.getElementById('btn-spawn-agent-modal')?.addEventListener('click', () => this.promptSpawnAgent());

      const allAgents = [
        ...this.dynamicAgents.map(a => ({ ...a, is_dynamic: true })),
        ...this.staticAgents.filter(s => !this.dynamicAgents.some(d => d.agent_id === s.agent_id)).map(s => ({ ...s, is_dynamic: false }))
      ];

      container.innerHTML = `
        <div class="mcp-grid">
          ${allAgents.map(a => `
            <div class="mcp-card" style="border-color:${a.is_dynamic ? 'rgba(74,222,128,0.25)' : 'var(--glass-border)'}">
              <div>
                <div class="mcp-card-header">
                  <span class="mcp-name">
                    <i class="fa-solid ${a.is_dynamic ? 'fa-wand-magic-sparkles' : 'fa-microchip'}" style="color:${a.is_dynamic ? 'var(--accent-mint)' : 'var(--accent-violet)'};margin-right:6px"></i>
                    ${a.agent_id}
                  </span>
                  <span class="mcp-status-dot" title="${a.status || 'Active'}"></span>
                </div>
                <div style="font-size:10px;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:6px;">
                  Type: <span style="color:${a.is_dynamic ? 'var(--accent-mint)' : 'var(--accent-cyan)'}">${a.is_dynamic ? 'Hermes Dynamic Agent' : 'Core Pillar Worker'}</span> · Model: <code>${a.model_name || 'fast'}</code>
                </div>
                <p class="mcp-desc">${a.description || 'Autonomous worker participating in Mitchell Hive swarm.'}</p>
                <div style="font-size:11px;font-family:var(--font-mono);color:var(--text-muted);margin-bottom:8px;">
                  <i class="fa-solid fa-bolt"></i> Tools: ${a.tools_count || 12} accessible · In/Out: ${a.inbox_count || 0}/${a.outbox_count || 0}
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--glass-border);padding-top:8px;">
                <span style="font-size:11px;color:var(--accent-mint)"><i class="fa-solid fa-circle" style="font-size:7px;margin-right:4px;"></i>${a.status || 'Ready'}</span>
                <div style="display:flex;gap:4px;">
                  <button class="btn btn-secondary btn-sm" onclick="window.__runAgentPrompt('${a.agent_id}')"><i class="fa-solid fa-play"></i> Delegate</button>
                  ${a.is_dynamic ? `<button class="btn btn-secondary btn-sm" onclick="window.__destroyAgent('${a.agent_id}')" style="color:var(--accent-red)"><i class="fa-solid fa-trash"></i></button>` : ''}
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      window.__runAgentPrompt = async (agentId) => {
        const prompt = window.prompt(`Enter task for agent '${agentId}':`);
        if (!prompt) return;
        const resp = await fetch('/api/agents/dynamic', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'run', agent_id: agentId, message: prompt }),
        });
        const res = await resp.json();
        window.alert(`Response from ${agentId}:\n\n${res.response || JSON.stringify(res)}`);
        await this.loadData();
      };

      window.__destroyAgent = async (agentId) => {
        if (confirm(`Terminate dynamic agent '${agentId}'?`)) {
          await fetch('/api/agents/dynamic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'destroy', agent_id: agentId }),
          });
          await this.loadData();
        }
      };

    } else if (this.activeTab === 'mcp') {
      actionBar.innerHTML = `
        <div class="mcp-install-box">
          <i class="fa-solid fa-cloud-arrow-down" style="color:var(--accent-cyan);font-size:16px;"></i>
          <input type="text" id="mcp-install-input" placeholder="Type package to install live in real time (e.g. '@modelcontextprotocol/server-postgres')..." />
          <button class="btn btn-primary" id="mcp-install-btn"><i class="fa-solid fa-bolt"></i> Install Real-Time</button>
        </div>
      `;

      const installInput = document.getElementById('mcp-install-input');
      const installBtn = document.getElementById('mcp-install-btn');
      const triggerInstall = async () => {
        const pkg = installInput?.value.trim();
        if (pkg) {
          await this.installMCP(pkg);
          if (installInput) installInput.value = '';
        }
      };
      installInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter') triggerInstall(); });
      installBtn?.addEventListener('click', triggerInstall);

      container.innerHTML = `
        <div class="mcp-grid">
          ${this.mcpServers.map(s => `
            <div class="mcp-card">
              <div>
                <div class="mcp-card-header">
                  <span class="mcp-name"><i class="fa-solid fa-server" style="color:var(--accent-cyan);margin-right:6px"></i>${s.name || s.server_name}</span>
                  <span class="mcp-status-dot" title="Live Connected"></span>
                </div>
                <p class="mcp-desc">Exposing ${(s.tools || []).length} tool bindings via Model Context Protocol stdio.</p>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px;">
                  ${(s.tools || []).map(t => `<span class="active-project-pill" style="font-size:10px;">${typeof t === 'string' ? t : t.name}</span>`).join('')}
                </div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--glass-border);padding-top:8px;">
                <span style="font-size:11px;color:var(--accent-mint);"><i class="fa-solid fa-bolt"></i> Live Connected</span>
                <button class="btn btn-secondary btn-sm" onclick="window.__removeMCP('${s.name || s.server_name}')"><i class="fa-solid fa-trash"></i> Remove</button>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      window.__removeMCP = async (name) => {
        await fetch('/api/mcp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'remove', server_name: name }),
        });
        await this.loadData();
      };

    } else if (this.activeTab === 'skills') {
      actionBar.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;background:var(--bg-surface);border:1px solid var(--glass-border);border-radius:var(--radius-lg);padding:10px 16px;">
          <div>
            <div style="font-weight:700;font-size:13px;color:var(--accent-violet);"><i class="fa-solid fa-scroll"></i> Procedural Skills Library</div>
            <div style="font-size:11.5px;color:var(--text-secondary);">Multi-step deterministic workflows, tool chains, and procedural heuristics.</div>
          </div>
          <button class="btn btn-primary btn-sm" id="btn-create-skill-modal"><i class="fa-solid fa-plus"></i> Create Skill</button>
        </div>
      `;

      document.getElementById('btn-create-skill-modal')?.addEventListener('click', () => this.promptCreateSkill());

      container.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
          ${this.skills.map(s => `
            <div style="background:var(--bg-surface);border:1px solid var(--glass-border);border-radius:var(--radius-md);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;">
              <div>
                <div style="font-weight:700;font-size:13px;font-family:var(--font-mono)"><i class="fa-solid fa-scroll" style="color:var(--accent-violet);margin-right:8px;"></i>${s.name}</div>
                <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${s.description}</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="window.__runSkill('${s.name}')"><i class="fa-solid fa-play"></i> Run</button>
            </div>
          `).join('')}
        </div>
      `;

      window.__runSkill = async (name) => {
        const resp = await fetch('/api/skills', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'execute', name: name }),
        });
        const res = await resp.json();
        window.alert(`Skill ${name} executed:\n${JSON.stringify(res, null, 2)}`);
      };

    } else if (this.activeTab === 'connectors') {
      actionBar.innerHTML = '';
      container.innerHTML = `
        <div class="mcp-grid">
          <div class="mcp-card">
            <div>
              <div class="mcp-card-header">
                <span class="mcp-name"><i class="fa-brands fa-whatsapp" style="color:var(--accent-mint);margin-right:6px"></i>WhatsApp Connector</span>
                <span class="mcp-status-dot"></span>
              </div>
              <p class="mcp-desc">Integration via @lharries/whatsapp-mcp. Full duplex messaging, chats, media streaming.</p>
              <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:8px;">Tools: send_message, list_chats, send_media</div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--glass-border);padding-top:8px;">
              <span class="status-badge-inline" style="color:var(--accent-mint)">Connected</span>
              <button class="btn btn-secondary btn-sm" onclick="alert('WhatsApp Bridge Active')">Configure</button>
            </div>
          </div>

          <div class="mcp-card">
            <div>
              <div class="mcp-card-header">
                <span class="mcp-name"><i class="fa-solid fa-house-signal" style="color:var(--accent-cyan);margin-right:6px"></i>Home Assistant Bridge</span>
                <span class="mcp-status-dot"></span>
              </div>
              <p class="mcp-desc">Local smart home IoT mesh covering lights, HVAC climate, switches, and presence scenes.</p>
              <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:8px;">Tools: list_entities, call_service</div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--glass-border);padding-top:8px;">
              <span class="status-badge-inline" style="color:var(--accent-mint)">Connected</span>
              <button class="btn btn-secondary btn-sm" onclick="alert('Home Assistant Bridge Active')">Configure</button>
            </div>
          </div>
        </div>
      `;
    }
  }

  async installMCP(packageName) {
    const status = document.getElementById('mcp-install-status');
    if (status) {
      status.innerHTML = `<span style="color:var(--accent-cyan);"><i class="fa-solid fa-spinner fa-spin"></i> Installing & launching MCP '${packageName}'...</span>`;
    }

    try {
      const resp = await fetch('/api/mcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'install_package', package: packageName }),
      });
      const data = await resp.json();
      if (status) {
        status.innerHTML = `<span style="color:var(--accent-mint);"><i class="fa-solid fa-check"></i> MCP '${data.server_name || packageName}' connected successfully!</span>`;
      }
      await this.loadData();
    } catch (e) {
      if (status) {
        status.innerHTML = `<span style="color:var(--accent-red);"><i class="fa-solid fa-circle-exclamation"></i> Installation error: ${e.message}</span>`;
      }
    }
  }

  async promptSpawnAgent() {
    const name = window.prompt('Enter Dynamic Agent Name (e.g. "DataAnalyst", "CodeReviewer"):', 'CustomWorker');
    if (!name) return;
    const role = window.prompt('Agent role / description:', 'Specialized subagent for autonomous execution');
    const prompt = window.prompt('System prompt instructions:', `You are ${name}. Carry out tasks autonomously using available tools.`);
    const model = window.prompt('Model tier ("fast", "think", "deep", "pro"):', 'fast') || 'fast';

    try {
      await fetch('/api/agents/dynamic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'spawn',
          name: name,
          description: role,
          system_prompt: prompt,
          model: model,
        }),
      });
      await this.loadData();
    } catch (e) {
      alert('Spawn error: ' + e.message);
    }
  }

  async promptCreateSkill() {
    const name = window.prompt('Enter skill name (e.g. "github_sync_and_pr"):');
    if (!name) return;
    const desc = window.prompt('Skill description:');
    try {
      await fetch('/api/skills', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', name: name, description: desc }),
      });
      await this.loadData();
    } catch (e) {
      alert('Skill creation error: ' + e.message);
    }
  }
}
