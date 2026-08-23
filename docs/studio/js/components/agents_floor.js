/**
 * Multi-Agent Floor Component (Under One Roof)
 * Coordinates Claude Code, Grok, Antigravity, OpenCode, and Codex in unified terminal cards.
 */

export class AgentsFloorStudio {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.activeAgents = [];
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="harness-wrapper">
        <!-- Harness Header -->
        <div class="harness-header">
          <div class="harness-header-left">
            <span class="harness-title"><i class="fa-solid fa-diagram-project" style="color:var(--accent-purple);margin-right:8px"></i>Multi-Agent Floor (Under One Roof)</span>
            <span class="badge badge-purple">Munder-Difflin Orchestrator</span>
          </div>
          <div class="harness-header-actions">
            <button class="btn btn-secondary btn-sm" id="harness-refresh-btn"><i class="fa-solid fa-rotate"></i> Refresh</button>
            <button class="btn btn-primary btn-sm" id="harness-dispatch-btn"><i class="fa-solid fa-paper-plane"></i> Dispatch Goal</button>
          </div>
        </div>

        <!-- Available Agents Cards -->
        <div class="agent-roster-title"><i class="fa-solid fa-users-gear"></i> Integrated CLI Agents</div>
        <div class="agent-roster-grid" id="agent-roster-grid">
          <div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Scanning agent CLIs on PATH...</div>
        </div>

        <!-- Active Agent Sessions Stream -->
        <div class="agent-roster-title" style="margin-top:24px;"><i class="fa-solid fa-terminal"></i> Active Coding Sessions</div>
        <div class="active-sessions-stream" id="active-sessions-stream">
          <div class="empty-state">
            <i class="fa-solid fa-code-fork"></i>
            <p>No active CLI agent sessions running. Dispatch a task to Claude Code or Grok to observe execution.</p>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadAgents();
  }

  bindEvents() {
    document.getElementById('harness-refresh-btn')?.addEventListener('click', () => this.loadAgents());
    document.getElementById('harness-dispatch-btn')?.addEventListener('click', () => this.promptDispatch());
  }

  async loadAgents() {
    const roster = document.getElementById('agent-roster-grid');
    const sessionsContainer = document.getElementById('active-sessions-stream');

    try {
      const resp = await fetch('/api/harness');
      const data = await resp.json();
      const agents = data.supported_agents || [];
      const sessions = data.active_sessions || [];

      // Render roster
      let rosterHtml = '';
      for (const a of agents) {
        const badge = a.installed
          ? '<span class="badge badge-green">Installed</span>'
          : '<span class="badge badge-yellow">Integrated</span>';

        rosterHtml += `
          <div class="agent-card">
            <div class="agent-card-top">
              <div class="agent-name-box">
                <i class="fa-solid fa-robot agent-avatar-icon"></i>
                <div class="agent-name">${a.name}</div>
              </div>
              ${badge}
            </div>
            <div class="agent-desc">${a.description}</div>
            <button class="btn btn-secondary btn-sm agent-run-btn" data-id="${a.id}">Dispatch ${a.id}</button>
          </div>
        `;
      }
      roster.innerHTML = rosterHtml;

      // Bind run buttons
      document.querySelectorAll('.agent-run-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const agentId = btn.dataset.id;
          const promptText = prompt(`Enter coding task for ${agentId}:`);
          if (promptText) this.dispatchAgent(agentId, promptText);
        });
      });

      // Render active sessions
      if (sessions.length) {
        let sessHtml = '';
        for (const s of sessions) {
          sessHtml += `
            <div class="agent-terminal-card">
              <div class="terminal-card-header">
                <div>
                  <strong>${s.display_name}</strong>
                  <span class="badge badge-purple" style="margin-left:8px;">${s.status.toUpperCase()}</span>
                </div>
                <div class="terminal-meta">${s.session_id}</div>
              </div>
              <pre class="terminal-buffer"><code>${s.output_buffer || 'Running...'}</code></pre>
            </div>
          `;
        }
        sessionsContainer.innerHTML = sessHtml;
      }
    } catch (e) {
      roster.innerHTML = `<div class="empty-state"><p>Error loading harness: ${e.message}</p></div>`;
    }
  }

  promptDispatch() {
    const promptText = prompt('Enter unified goal for Mitchell multi-agent orchestrator:');
    if (promptText) {
      this.dispatchAgent('claude', promptText);
    }
  }

  async dispatchAgent(agentId, promptText) {
    try {
      const resp = await fetch('/api/harness', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'start',
          agent_id: agentId,
          prompt: promptText,
        }),
      });
      const data = await resp.json();
      await this.loadAgents();
      // Poll session status for a few seconds
      setTimeout(() => this.loadAgents(), 1000);
      setTimeout(() => this.loadAgents(), 2500);
    } catch (e) {
      alert(`Dispatch failed: ${e.message}`);
    }
  }
}
