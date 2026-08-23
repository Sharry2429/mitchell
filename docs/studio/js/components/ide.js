/**
 * MitchellIDE — Monaco-Powered Antigravity Agentic IDE
 * Layout:
 * ┌─────────────┬──────────────────────────────┬─────────────┐
 * │  File Tree  │        Editor (Monaco)       │   Chat      │
 * │  (left)     │                              │  (right,    │
 * │             │  tabs of open files          │  minimized) │
 * │             │                              │             │
 * │             ├──────────────────────────────┤             │
 * │             │  Terminal (Mitchell + User)  │             │
 * └─────────────┴──────────────────────────────┴─────────────┘
 */

export class MitchellIDE {
  constructor(containerId = 'ide-container') {
    this.container = document.getElementById(containerId);
    this.monacoEditor = null;
    this.activeFile = null;
    this.openTabs = []; // { path, name, content, modified }
    this.cmdHistory = [];
    this.cmdHistoryIdx = -1;
    this.currentProject = null;
    this.currentTerminalTab = 'user';
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="ide-container">
        <!-- Top Toolbar -->
        <div class="ide-top-toolbar">
          <div class="ide-toolbar-left">
            <span class="ide-project-title" style="font-weight:700;font-size:12px;font-family:var(--font-mono)">
              <i class="fa-solid fa-code" style="color:var(--accent-cyan);margin-right:6px"></i>Mitchell IDE
            </span>
            <span class="active-project-pill" id="ide-workspace-pill">Workspace: Root</span>
          </div>
          <div class="ide-toolbar-right">
            <button class="btn btn-secondary btn-sm" id="ide-btn-new-file" title="New File"><i class="fa-solid fa-file-circle-plus"></i> New File</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-new-folder" title="New Folder"><i class="fa-solid fa-folder-plus"></i> Folder</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-git" title="Git Status"><i class="fa-solid fa-code-branch" style="color:var(--accent-blue)"></i> Git</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-tests" title="Run Pytest"><i class="fa-solid fa-vial" style="color:var(--accent-violet)"></i> Tests</button>
            <button class="btn btn-primary btn-sm" id="ide-btn-run" title="Execute Active File (▶ Run)"><i class="fa-solid fa-play" style="color:#000"></i> Run</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-save" title="Save File (Ctrl+S)"><i class="fa-solid fa-floppy-disk"></i> Save</button>
          </div>
        </div>

        <!-- 3-Pane Main Split Layout -->
        <div class="ide-3pane-layout">
          <!-- Left Pane: File Tree Explorer -->
          <div class="ide-tree-pane">
            <div class="ide-pane-header">
              <span>EXPLORER</span>
              <div style="display:flex;gap:4px;">
                <button class="icon-btn" id="ide-tree-refresh" title="Refresh Tree" style="width:20px;height:20px;font-size:10px;"><i class="fa-solid fa-rotate"></i></button>
              </div>
            </div>
            <div class="ide-tree-scroll" id="ide-tree-content">
              <div style="padding:12px;color:var(--text-muted);font-size:11px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading workspace...</div>
            </div>
          </div>

          <!-- Center Pane: Monaco Editor & Terminal Drawer -->
          <div class="ide-center-pane">
            <!-- Tabs Bar -->
            <div class="ide-tabs-bar" id="ide-tabs-bar">
              <!-- Dynamically populated open file tabs -->
            </div>

            <!-- Monaco Editor Viewport -->
            <div class="ide-monaco-viewport" id="ide-monaco-viewport">
              <div id="ide-monaco-editor"></div>
              <textarea id="ide-fallback-editor" class="ide-fallback-textarea" style="display:none;" spellcheck="false" placeholder="// Select a file from the explorer on the left..."></textarea>
            </div>

            <!-- Bottom Terminal Drawer -->
            <div class="ide-terminal-drawer">
              <div class="term-header">
                <div class="term-tabs">
                  <button class="term-tab-btn active" data-tab="user"><i class="fa-solid fa-terminal"></i> User Terminal</button>
                  <button class="term-tab-btn" data-tab="mitchell"><i class="fa-solid fa-robot"></i> Mitchell Agent</button>
                  <button class="term-tab-btn" data-tab="tests"><i class="fa-solid fa-vial"></i> Test Runner</button>
                  <button class="term-tab-btn" data-tab="git"><i class="fa-solid fa-code-branch"></i> Git Output</button>
                </div>
                <div style="display:flex;gap:4px;">
                  <button class="icon-btn" id="term-clear-btn" title="Clear Console" style="width:22px;height:22px;font-size:10px;"><i class="fa-solid fa-ban"></i></button>
                </div>
              </div>
              <div class="term-output" id="term-output-stream">
                <div class="term-line success"><i class="fa-solid fa-check"></i> Mitchell Agentic IDE Environment initialized. Ready.</div>
              </div>
              <div class="term-input-line">
                <span class="term-prompt">mitchell@studio $</span>
                <input type="text" id="term-interactive-input" placeholder="Type a shell command or execute in workspace..." autocomplete="off" />
              </div>
            </div>
          </div>

          <!-- Right Pane: Minimized / Docked AI Composer Chat -->
          <div class="ide-right-dock" id="ide-right-dock">
            <div class="dock-header">
              <span><i class="fa-solid fa-sparkles" style="color:var(--accent-violet);margin-right:6px"></i>AI Composer</span>
              <button class="icon-btn" id="dock-collapse-btn" title="Toggle AI Dock" style="width:22px;height:22px;font-size:10px;"><i class="fa-solid fa-chevron-right"></i></button>
            </div>
            <div class="dock-messages" id="dock-messages-list">
              <div style="background:var(--bg-elevated);padding:8px 10px;border-radius:var(--radius-sm);font-size:12px;">
                I'm active in your workspace. Ask me to refactor code, fix bugs, or run tests directly.
              </div>
            </div>
            <div class="dock-input-wrap">
              <textarea id="dock-prompt-input" placeholder="Instruct Mitchell on this file (e.g. 'Refactor to async', 'Fix tests')..."></textarea>
              <div style="display:flex;justify-content:flex-end;margin-top:6px;gap:6px;">
                <button class="btn btn-primary btn-sm" id="dock-send-btn"><i class="fa-solid fa-arrow-up"></i> Apply</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    await this.initMonaco();
    this.bindEvents();
    await this.loadFileTree();

    // Open default welcome file or manager.py
    this.openFile('mitchell/cli.py');
  }

  async initMonaco() {
    const editorElem = document.getElementById('ide-monaco-editor');
    const fallback = document.getElementById('ide-fallback-editor');

    if (window.require && window.monaco) {
      try {
        this.monacoEditor = window.monaco.editor.create(editorElem, {
          value: '// Loading file...',
          language: 'python',
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: true },
          fontSize: 13,
          fontFamily: "'JetBrains Mono', monospace",
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          tabSize: 4,
          insertSpaces: true,
          renderWhitespace: 'selection',
        });

        // Setup save shortcut
        this.monacoEditor.addCommand(window.monaco.KeyMod.CtrlCmd | window.monaco.KeyCode.KeyS, () => {
          this.saveActiveFile();
        });
        return;
      } catch (err) {
        console.warn('Monaco init error, falling back to textarea', err);
      }
    }

    // Try loading via requirejs if loader present
    if (window.require && !window.monaco) {
      window.require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
      window.require(['vs/editor/editor.main'], () => {
        try {
          this.monacoEditor = window.monaco.editor.create(editorElem, {
            value: '// Loading file...',
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: true },
            fontSize: 13,
            fontFamily: "'JetBrains Mono', monospace",
          });
          this.monacoEditor.addCommand(window.monaco.KeyMod.CtrlCmd | window.monaco.KeyCode.KeyS, () => {
            this.saveActiveFile();
          });
          if (this.activeFile) {
            this.openFile(this.activeFile);
          }
        } catch (e) {
          if (fallback) fallback.style.display = 'block';
        }
      });
      return;
    }

    if (fallback) fallback.style.display = 'block';
  }

  bindEvents() {
    document.getElementById('ide-tree-refresh')?.addEventListener('click', () => this.loadFileTree());
    document.getElementById('ide-btn-save')?.addEventListener('click', () => this.saveActiveFile());
    document.getElementById('ide-btn-run')?.addEventListener('click', () => this.runActiveFile());
    document.getElementById('ide-btn-tests')?.addEventListener('click', () => this.runTests());
    document.getElementById('ide-btn-git')?.addEventListener('click', () => this.checkGitStatus());
    document.getElementById('ide-btn-new-file')?.addEventListener('click', () => this.promptNewFile());
    document.getElementById('ide-btn-new-folder')?.addEventListener('click', () => this.promptNewFolder());
    document.getElementById('term-clear-btn')?.addEventListener('click', () => {
      const out = document.getElementById('term-output-stream');
      if (out) out.innerHTML = '';
    });

    // Terminal Tabs
    document.querySelectorAll('.term-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.term-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentTerminalTab = btn.dataset.tab;
      });
    });

    // Terminal Input
    const termInput = document.getElementById('term-interactive-input');
    termInput?.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        const cmd = termInput.value.trim();
        if (cmd) {
          this.cmdHistory.push(cmd);
          this.cmdHistoryIdx = this.cmdHistory.length;
          termInput.value = '';
          await this.executeCommand(cmd);
        }
      } else if (e.key === 'ArrowUp') {
        if (this.cmdHistory.length > 0 && this.cmdHistoryIdx > 0) {
          this.cmdHistoryIdx--;
          termInput.value = this.cmdHistory[this.cmdHistoryIdx] || '';
        }
      } else if (e.key === 'ArrowDown') {
        if (this.cmdHistoryIdx < this.cmdHistory.length - 1) {
          this.cmdHistoryIdx++;
          termInput.value = this.cmdHistory[this.cmdHistoryIdx] || '';
        } else {
          this.cmdHistoryIdx = this.cmdHistory.length;
          termInput.value = '';
        }
      }
    });

    // AI Dock prompt
    const dockSend = document.getElementById('dock-send-btn');
    const dockInput = document.getElementById('dock-prompt-input');
    dockSend?.addEventListener('click', () => this.sendDockPrompt());
    dockInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        this.sendDockPrompt();
      }
    });

    // Keyboard global shortcuts
    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const idePanel = document.getElementById('panel-ide');
        if (idePanel && idePanel.classList.contains('active')) {
          e.preventDefault();
          this.saveActiveFile();
        }
      }
    });
  }

  async loadFileTree(rootPath = '') {
    const treeContainer = document.getElementById('ide-tree-content');
    if (!treeContainer) return;

    try {
      const resp = await fetch(`/api/ide?root=${encodeURIComponent(rootPath)}`);
      const data = await resp.json();
      const tree = data.file_tree || [];
      this.renderTreeNodes(tree, treeContainer);
    } catch (e) {
      treeContainer.innerHTML = `<div style="padding:10px;color:var(--text-muted)">Workspace tree online</div>`;
    }
  }

  renderTreeNodes(nodes, container) {
    if (!nodes || nodes.length === 0) {
      container.innerHTML = `<div style="padding:8px;color:var(--text-muted)">No files found.</div>`;
      return;
    }

    container.innerHTML = '';
    const sorted = [...nodes].sort((a, b) => (b.is_dir ? 1 : 0) - (a.is_dir ? 1 : 0) || a.name.localeCompare(b.name));

    sorted.forEach(node => {
      const item = document.createElement('div');
      item.className = 'tree-node';
      item.dataset.path = node.path;
      item.dataset.isDir = node.is_dir;
      item.style.position = 'relative';

      const icon = node.is_dir ? 'fa-folder' : this.getFileIcon(node.name);
      const iconColor = node.is_dir ? 'var(--accent-amber)' : this.getFileColor(node.name);

      item.innerHTML = `
        <i class="fa-solid ${icon}" style="color:${iconColor};font-size:11px;width:14px"></i>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;margin-right:6px;">${node.name}</span>
        <div class="tree-node-actions" style="display:none;gap:4px;">
          <button class="node-action-btn copy-path" title="Copy Path" style="font-size:10px;color:var(--text-muted);"><i class="fa-solid fa-copy"></i></button>
          <button class="node-action-btn rename-node" title="Rename" style="font-size:10px;color:var(--text-muted);"><i class="fa-solid fa-pen"></i></button>
          <button class="node-action-btn del-node" title="Delete" style="font-size:10px;color:var(--text-muted);"><i class="fa-solid fa-trash"></i></button>
        </div>
      `;

      const actions = item.querySelector('.tree-node-actions');
      item.addEventListener('mouseenter', () => { if (actions) actions.style.display = 'flex'; });
      item.addEventListener('mouseleave', () => { if (actions) actions.style.display = 'none'; });

      item.querySelector('.copy-path')?.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(node.path);
        this.logTerminal(`[Copied Path] ${node.path}`, 'info');
      });

      item.querySelector('.rename-node')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        const newName = window.prompt(`Rename ${node.name} to:`, node.name);
        if (newName && newName !== node.name) {
          const dir = node.path.includes('/') ? node.path.substring(0, node.path.lastIndexOf('/')) : (node.path.includes('\\') ? node.path.substring(0, node.path.lastIndexOf('\\')) : '');
          const newPath = dir ? `${dir}/${newName}` : newName;
          await this.executeCommand(`mv "${node.path}" "${newPath}"`);
          await this.loadFileTree();
        }
      });

      item.querySelector('.del-node')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (window.confirm(`Delete ${node.name}?`)) {
          await this.executeCommand(`rm -rf "${node.path}"`);
          await this.loadFileTree();
        }
      });

      item.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (node.is_dir) {
          // Toggle directory expansion
          let childContainer = item.nextElementSibling;
          if (childContainer && childContainer.classList.contains('tree-children')) {
            childContainer.style.display = childContainer.style.display === 'none' ? 'block' : 'none';
          } else {
            childContainer = document.createElement('div');
            childContainer.className = 'tree-children';
            childContainer.style.paddingLeft = '14px';
            item.after(childContainer);
            this.loadFileTree(node.path);
          }
        } else {
          document.querySelectorAll('.tree-node').forEach(n => n.classList.remove('active'));
          item.classList.add('active');
          await this.openFile(node.path);
        }
      });

      container.appendChild(item);
    });
  }

  getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
      case 'py': return 'fa-brands fa-python';
      case 'js': case 'jsx': case 'ts': case 'tsx': return 'fa-brands fa-js';
      case 'html': return 'fa-brands fa-html5';
      case 'css': return 'fa-brands fa-css3-alt';
      case 'json': return 'fa-solid fa-code';
      case 'md': return 'fa-solid fa-file-lines';
      case 'sh': case 'bash': case 'ps1': return 'fa-solid fa-terminal';
      default: return 'fa-solid fa-file-code';
    }
  }

  getFileColor(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
      case 'py': return '#4ade80';
      case 'js': case 'ts': return '#fbbf24';
      case 'html': return '#fb923c';
      case 'css': return '#22d3ee';
      case 'json': return '#a78bfa';
      case 'md': return '#60a5fa';
      default: return 'var(--text-secondary)';
    }
  }

  getMonacoLanguage(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    switch (ext) {
      case 'py': return 'python';
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'json': return 'json';
      case 'md': return 'markdown';
      case 'sh': case 'bash': case 'ps1': return 'shell';
      case 'sql': return 'sql';
      case 'rs': return 'rust';
      case 'cpp': case 'c': case 'h': return 'cpp';
      default: return 'plaintext';
    }
  }

  async openFile(filePath) {
    if (!filePath) return;
    this.activeFile = filePath;
    const fileName = filePath.split('/').pop().split('\\').pop();

    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'read_file', path: filePath }),
      });
      const data = await resp.json();
      const content = data.content || '';

      // Update tabs
      let tab = this.openTabs.find(t => t.path === filePath);
      if (!tab) {
        tab = { path: filePath, name: fileName, content: content, modified: false };
        this.openTabs.push(tab);
      }
      this.renderTabs();

      // Set editor content
      if (this.monacoEditor) {
        const model = this.monacoEditor.getModel();
        const lang = this.getMonacoLanguage(fileName);
        if (model) {
          window.monaco.editor.setModelLanguage(model, lang);
          this.monacoEditor.setValue(content);
        }
      } else {
        const fallback = document.getElementById('ide-fallback-editor');
        if (fallback) fallback.value = content;
      }

      this.logTerminal(`[Editor] Opened ${filePath}`, 'info');
    } catch (e) {
      this.logTerminal(`[Error] Failed to open ${filePath}: ${e.message}`, 'error');
    }
  }

  renderTabs() {
    const tabsBar = document.getElementById('ide-tabs-bar');
    if (!tabsBar) return;

    tabsBar.innerHTML = '';
    this.openTabs.forEach(tab => {
      const tabElem = document.createElement('div');
      tabElem.className = `ide-tab ${tab.path === this.activeFile ? 'active' : ''}`;
      tabElem.innerHTML = `
        <i class="${this.getFileIcon(tab.name)}" style="color:${this.getFileColor(tab.name)};font-size:11px"></i>
        <span>${tab.name}${tab.modified ? ' ●' : ''}</span>
        <span class="tab-close">×</span>
      `;

      tabElem.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-close')) {
          e.stopPropagation();
          this.closeTab(tab.path);
        } else {
          this.openFile(tab.path);
        }
      });

      tabsBar.appendChild(tabElem);
    });
  }

  closeTab(filePath) {
    this.openTabs = this.openTabs.filter(t => t.path !== filePath);
    if (this.activeFile === filePath) {
      const next = this.openTabs[this.openTabs.length - 1];
      if (next) {
        this.openFile(next.path);
      } else {
        this.activeFile = null;
        if (this.monacoEditor) this.monacoEditor.setValue('');
        this.renderTabs();
      }
    } else {
      this.renderTabs();
    }
  }

  async saveActiveFile() {
    if (!this.activeFile) return;

    let content = '';
    if (this.monacoEditor) {
      content = this.monacoEditor.getValue();
    } else {
      content = document.getElementById('ide-fallback-editor')?.value || '';
    }

    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'write_file', path: this.activeFile, content: content }),
      });
      const data = await resp.json();
      if (data.success) {
        this.logTerminal(`[Saved] ${this.activeFile} (+${data.lines_added}, -${data.lines_removed})`, 'success');
        const tab = this.openTabs.find(t => t.path === this.activeFile);
        if (tab) tab.modified = false;
        this.renderTabs();
      } else {
        this.logTerminal(`[Syntax Error] ${data.error_message}`, 'error');
      }
    } catch (e) {
      this.logTerminal(`[Save Error] ${e.message}`, 'error');
    }
  }

  async runActiveFile() {
    if (!this.activeFile) {
      this.logTerminal(`[Run] No active file selected.`, 'error');
      return;
    }

    this.logTerminal(`$ python "${this.activeFile}"`, 'cmd');
    await this.executeCommand(`python "${this.activeFile}"`);
  }

  async runTests() {
    this.logTerminal(`$ python -m pytest tests/`, 'cmd');
    await this.executeCommand(`python -m pytest tests/`);
  }

  async checkGitStatus() {
    this.logTerminal(`$ git status`, 'cmd');
    await this.executeCommand(`git status`);
  }

  async executeCommand(cmd) {
    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'run_command', command: cmd }),
      });
      const data = await resp.json();

      if (data.stdout) {
        this.logTerminal(data.stdout, 'out');
      }
      if (data.stderr) {
        this.logTerminal(data.stderr, 'error');
      }
      if (data.exit_code === 0) {
        this.logTerminal(`[Exit: 0 in ${data.duration_s}s]`, 'success');
      } else {
        this.logTerminal(`[Exit: ${data.exit_code} in ${data.duration_s}s]`, 'error');
      }
    } catch (e) {
      this.logTerminal(`[Execution Error] ${e.message}`, 'error');
    }
  }

  logTerminal(text, type = 'out') {
    const stream = document.getElementById('term-output-stream');
    if (!stream) return;

    const line = document.createElement('div');
    line.className = `term-line ${type}`;
    line.textContent = text;
    stream.appendChild(line);
    stream.scrollTop = stream.scrollHeight;
  }

  async sendDockPrompt() {
    const input = document.getElementById('dock-prompt-input');
    const msgList = document.getElementById('dock-messages-list');
    const prompt = input?.value.trim();
    if (!prompt) return;

    input.value = '';
    const userBubble = document.createElement('div');
    userBubble.style.cssText = 'background:var(--bg-active);padding:8px 10px;border-radius:var(--radius-sm);color:#fff;font-size:12px;';
    userBubble.textContent = prompt;
    msgList?.appendChild(userBubble);

    const thinking = document.createElement('div');
    thinking.style.cssText = 'color:var(--accent-violet);font-size:11px;padding:4px;';
    thinking.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Mitchell refactoring...`;
    msgList?.appendChild(thinking);
    msgList.scrollTop = msgList.scrollHeight;

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `[File: ${this.activeFile || 'Workspace'}] ${prompt}` }),
      });
      const data = await resp.json();
      thinking.remove();

      const aiBubble = document.createElement('div');
      aiBubble.style.cssText = 'background:var(--bg-elevated);border:1px solid var(--glass-border);padding:10px;border-radius:var(--radius-sm);font-size:12px;';
      aiBubble.innerHTML = `<strong>Mitchell:</strong><br>${data.response}`;
      msgList?.appendChild(aiBubble);
      msgList.scrollTop = msgList.scrollHeight;
    } catch (e) {
      thinking.innerHTML = `<span style="color:var(--accent-red)">Error: ${e.message}</span>`;
    }
  }

  promptNewFile() {
    const name = window.prompt('Enter file path / name:', 'new_module.py');
    if (name) {
      this.openFile(name);
    }
  }

  promptNewFolder() {
    const name = window.prompt('Enter folder name:', 'new_folder');
    if (name) {
      this.executeCommand(`mkdir -p "${name}"`).then(() => this.loadFileTree());
    }
  }
}
