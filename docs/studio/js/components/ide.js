/**
 * MitchellIDE — Inbuilt Agentic IDE Component (1-to-1 Antigravity/VS Code experience)
 * Handles file tree explorer, multi-tab editor, diff viewer, terminal, and agent patch review.
 */

export class MitchellIDE {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.activeFile = null;
    this.openTabs = [];
    this.currentProject = null;
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="ide-wrapper">
        <!-- IDE Top Toolbar -->
        <div class="ide-toolbar">
          <div class="ide-toolbar-left">
            <span class="ide-project-title"><i class="fa-solid fa-code" style="color:var(--accent-purple);margin-right:6px"></i>MitchellIDE</span>
            <span class="badge badge-purple" id="ide-current-project">Workspace</span>
          </div>
          <div class="ide-toolbar-actions">
            <button class="btn btn-secondary btn-sm" id="ide-btn-new-file" title="New File"><i class="fa-solid fa-plus"></i> New File</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-run-tests" title="Run Pytest"><i class="fa-solid fa-play" style="color:var(--accent-green)"></i> Run Tests</button>
            <button class="btn btn-secondary btn-sm" id="ide-btn-git-status" title="Git Status"><i class="fa-solid fa-code-branch" style="color:var(--accent-blue)"></i> Git</button>
            <button class="btn btn-primary btn-sm" id="ide-btn-save-file" title="Save File (Ctrl+S)"><i class="fa-solid fa-floppy-disk"></i> Save</button>
          </div>
        </div>

        <!-- IDE Main Layout: File Tree Sidebar + Editor Canvas -->
        <div class="ide-main-split">
          <!-- Left File Explorer -->
          <div class="ide-file-tree-pane">
            <div class="ide-pane-header">
              <span>EXPLORER</span>
              <button class="icon-btn-sm" id="ide-refresh-tree" title="Refresh Tree"><i class="fa-solid fa-rotate"></i></button>
            </div>
            <div class="ide-tree-scroll" id="ide-tree-content">
              <div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading file tree...</div>
            </div>
          </div>

          <!-- Center Code Editor Pane -->
          <div class="ide-editor-pane">
            <!-- Open File Tabs -->
            <div class="ide-tabs-bar" id="ide-tabs-bar">
              <div class="ide-tab active" data-path="welcome">
                <i class="fa-solid fa-file-code"></i>
                <span class="tab-label">Welcome.md</span>
              </div>
            </div>

            <!-- Code Editor Area -->
            <div class="ide-editor-container" id="ide-editor-container">
              <textarea id="ide-code-textarea" class="ide-code-textarea" spellcheck="false" placeholder="// Select a file from the explorer to begin editing..."></textarea>
            </div>

            <!-- Bottom Console / Terminal Drawer -->
            <div class="ide-terminal-drawer" id="ide-terminal-drawer">
              <div class="ide-terminal-header">
                <div class="ide-terminal-tabs">
                  <span class="term-tab active"><i class="fa-solid fa-terminal"></i> Terminal</span>
                  <span class="term-tab"><i class="fa-solid fa-bug"></i> Test Runner</span>
                </div>
                <button class="icon-btn-sm" id="ide-clear-term" title="Clear Console"><i class="fa-solid fa-ban"></i></button>
              </div>
              <div class="ide-terminal-output" id="ide-terminal-output">
                <span class="term-line success">Mitchell Agentic IDE Environment initialized. Ready.</span>
              </div>
              <div class="ide-terminal-input-bar">
                <span class="term-prompt">$</span>
                <input type="text" id="ide-term-input" placeholder="Execute command in workspace..." autocomplete="off" />
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadFileTree();
  }

  bindEvents() {
    document.getElementById('ide-refresh-tree')?.addEventListener('click', () => this.loadFileTree());
    document.getElementById('ide-btn-save-file')?.addEventListener('click', () => this.saveActiveFile());
    document.getElementById('ide-btn-run-tests')?.addEventListener('click', () => this.runTests());
    document.getElementById('ide-btn-git-status')?.addEventListener('click', () => this.checkGitStatus());
    document.getElementById('ide-btn-new-file')?.addEventListener('click', () => this.promptNewFile());

    // Terminal command execution
    const termInput = document.getElementById('ide-term-input');
    termInput?.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        const cmd = termInput.value.trim();
        if (cmd) {
          this.logTerminal(`$ ${cmd}`, 'cmd');
          termInput.value = '';
          await this.runTerminalCommand(cmd);
        }
      }
    });

    // Keyboard shortcuts (Ctrl+S)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const idePanel = document.getElementById('panel-ide');
        if (idePanel && idePanel.classList.contains('active')) {
          e.preventDefault();
          this.saveActiveFile();
        }
      }
    });
  }

  async loadFileTree() {
    const treeContainer = document.getElementById('ide-tree-content');
    try {
      const resp = await fetch('/api/ide?root=.');
      const data = await resp.json();
      const tree = data.file_tree;
      if (tree) {
        treeContainer.innerHTML = this.renderTreeNode(tree);
        this.bindTreeClicks();
      }
    } catch (e) {
      treeContainer.innerHTML = `<div class="empty-state"><p>Error loading directory: ${e.message}</p></div>`;
    }
  }

  renderTreeNode(node) {
    if (node.type === 'directory') {
      const childrenHtml = (node.children || []).map(c => this.renderTreeNode(c)).join('');
      return `
        <div class="tree-dir">
          <div class="tree-item tree-folder" data-path="${node.path}">
            <i class="fa-solid fa-folder tree-icon" style="color:var(--accent-purple)"></i>
            <span class="tree-name">${node.name}</span>
          </div>
          <div class="tree-children">${childrenHtml}</div>
        </div>
      `;
    } else {
      const icon = this.getFileIcon(node.extension);
      return `
        <div class="tree-item tree-file" data-path="${node.path}" data-name="${node.name}">
          <i class="${icon} tree-icon"></i>
          <span class="tree-name">${node.name}</span>
        </div>
      `;
    }
  }

  getFileIcon(ext) {
    switch (ext) {
      case 'py': return 'fa-brands fa-python file-icon-py';
      case 'js': return 'fa-brands fa-js file-icon-js';
      case 'html': return 'fa-brands fa-html5 file-icon-html';
      case 'css': return 'fa-brands fa-css3-alt file-icon-css';
      case 'json': return 'fa-solid fa-brackets-curly file-icon-json';
      case 'md': return 'fa-solid fa-file-lines file-icon-md';
      default: return 'fa-solid fa-file file-icon-default';
    }
  }

  bindTreeClicks() {
    document.querySelectorAll('.tree-file').forEach(el => {
      el.addEventListener('click', () => {
        const path = el.dataset.path;
        const name = el.dataset.name;
        this.openFile(path, name);
      });
    });

    document.querySelectorAll('.tree-folder').forEach(el => {
      el.addEventListener('click', () => {
        const children = el.nextElementSibling;
        if (children) {
          children.classList.toggle('collapsed');
          const icon = el.querySelector('.tree-icon');
          if (icon) {
            icon.className = children.classList.contains('collapsed')
              ? 'fa-solid fa-folder tree-icon'
              : 'fa-solid fa-folder-open tree-icon';
          }
        }
      });
    });
  }

  async openFile(path, name) {
    this.activeFile = { path, name };

    // Update tab bar
    const tabsBar = document.getElementById('ide-tabs-bar');
    tabsBar.innerHTML = `
      <div class="ide-tab active" data-path="${path}">
        <i class="fa-solid fa-file-code"></i>
        <span class="tab-label">${name}</span>
      </div>
    `;

    // Highlight selected item in tree
    document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('selected'));
    document.querySelector(`.tree-file[data-path="${CSS.escape(path)}"]`)?.classList.add('selected');

    const textarea = document.getElementById('ide-code-textarea');
    textarea.value = '// Loading file content...';

    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'read_file', path }),
      });
      const data = await resp.json();
      textarea.value = data.content || '';
      this.logTerminal(`Opened ${name} (${(data.content || '').length} chars)`, 'info');
    } catch (e) {
      textarea.value = `// Error reading file: ${e.message}`;
    }
  }

  async saveActiveFile() {
    if (!this.activeFile) {
      alert('No active file open to save.');
      return;
    }

    const textarea = document.getElementById('ide-code-textarea');
    const content = textarea.value;

    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'write_file',
          path: this.activeFile.path,
          content: content,
        }),
      });
      const data = await resp.json();
      if (data.success) {
        this.logTerminal(`Saved ${this.activeFile.name} (+${data.lines_added}, -${data.lines_removed})`, 'success');
      } else {
        this.logTerminal(`Save error: ${data.error_message}`, 'error');
      }
    } catch (e) {
      this.logTerminal(`Save request failed: ${e.message}`, 'error');
    }
  }

  async runTests() {
    this.logTerminal('Running automated test suite (pytest)...', 'info');
    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'run_tests' }),
      });
      const data = await resp.json();
      if (data.success) {
        this.logTerminal(`Tests Passed! ${data.tests_passed} passed in ${data.duration_s}s`, 'success');
      } else {
        this.logTerminal(`Test Failures: ${data.summary || data.stdout}`, 'error');
      }
    } catch (e) {
      this.logTerminal(`Test runner error: ${e.message}`, 'error');
    }
  }

  async checkGitStatus() {
    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'git_status' }),
      });
      const data = await resp.json();
      this.logTerminal(`Git Branch: ${data.branch || 'main'} | Clean: ${data.is_clean}`, 'info');
      if (data.modified_files?.length) {
        this.logTerminal(`Modified: ${data.modified_files.join(', ')}`, 'warning');
      }
      if (data.untracked_files?.length) {
        this.logTerminal(`Untracked: ${data.untracked_files.join(', ')}`, 'warning');
      }
    } catch (e) {
      this.logTerminal(`Git error: ${e.message}`, 'error');
    }
  }

  async runTerminalCommand(cmd) {
    try {
      const resp = await fetch('/api/ide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'run_command', command: cmd }),
      });
      const data = await resp.json();
      if (data.stdout) this.logTerminal(data.stdout, 'stdout');
      if (data.stderr) this.logTerminal(data.stderr, 'error');
    } catch (e) {
      this.logTerminal(`Execution error: ${e.message}`, 'error');
    }
  }

  logTerminal(text, type = 'stdout') {
    const term = document.getElementById('ide-terminal-output');
    if (!term) return;
    const line = document.createElement('div');
    line.className = `term-line ${type}`;
    line.textContent = text;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
  }

  promptNewFile() {
    const filename = prompt('Enter relative path for new file (e.g. src/app.py):');
    if (filename) {
      this.activeFile = { path: filename, name: filename.split('/').pop() };
      document.getElementById('ide-code-textarea').value = '';
      this.saveActiveFile();
      this.loadFileTree();
    }
  }
}
