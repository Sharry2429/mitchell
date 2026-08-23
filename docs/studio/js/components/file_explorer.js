/**
 * FileExplorerStudio — Lightweight Command-Driven File Explorer
 * Features:
 * - Filesystem browser with file operations (rename, delete, download, preview)
 * - Natural language grep search across code & workspace documents ("find document that contains X")
 * - One-click launch into Monaco IDE
 */

export class FileExplorerStudio {
  constructor(containerId = 'file-explorer-container') {
    this.container = document.getElementById(containerId);
    this.currentPath = '.';
    this.files = [];
    this.searchResults = [];
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="skills-container" style="max-width:1000px;margin:0 auto;padding:20px 24px;overflow-y:auto;height:100%;">
        <!-- Header -->
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--glass-border);padding-bottom:12px;margin-bottom:16px;">
          <div>
            <h2 style="font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px;">
              <i class="fa-solid fa-folder-tree" style="color:var(--accent-amber)"></i> Workspace Files & Search
            </h2>
            <p style="font-size:12px;color:var(--text-secondary);margin-top:2px;">
              Natural language search and lightweight file explorer.
            </p>
          </div>
          <div style="display:flex;gap:6px;">
            <button class="btn btn-secondary btn-sm" id="btn-files-refresh"><i class="fa-solid fa-rotate"></i> Refresh</button>
            <button class="btn btn-primary btn-sm" id="btn-files-open-ide"><i class="fa-solid fa-code"></i> Open in IDE</button>
          </div>
        </div>

        <!-- Natural Language Search Box -->
        <div class="mcp-install-box" style="margin-bottom:16px;">
          <i class="fa-solid fa-magnifying-glass" style="color:var(--accent-amber)"></i>
          <input type="text" id="file-grep-search-input" placeholder="Natural language search (e.g. 'find document containing API keys', 'functions in loop.py')..." />
          <button class="btn btn-primary" id="file-grep-search-btn"><i class="fa-solid fa-bolt"></i> Search</button>
        </div>

        <div id="file-search-results" style="margin-bottom:16px;display:none;"></div>

        <!-- Files Table / Grid -->
        <div style="background:var(--bg-surface);border:1px solid var(--glass-border);border-radius:var(--radius-lg);overflow:hidden;">
          <div style="padding:10px 14px;background:var(--bg-deep);border-bottom:1px solid var(--glass-border);font-weight:600;font-size:11.5px;display:flex;justify-content:space-between;">
            <span>Name</span>
            <span>Path</span>
          </div>
          <div id="file-list-body" style="max-height:400px;overflow-y:auto;padding:6px;">
            <div style="padding:16px;color:var(--text-muted);font-family:var(--font-mono)"><i class="fa-solid fa-spinner fa-spin"></i> Reading directory...</div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadDirectory();
  }

  bindEvents() {
    document.getElementById('btn-files-refresh')?.addEventListener('click', () => this.loadDirectory());
    document.getElementById('btn-files-open-ide')?.addEventListener('click', () => {
      if (window.__mitchellStudioController) {
        window.__mitchellStudioController.activatePanel('ide');
      }
    });

    const searchInput = document.getElementById('file-grep-search-input');
    const searchBtn = document.getElementById('file-grep-search-btn');

    const triggerSearch = async () => {
      const q = searchInput?.value.trim();
      if (q) await this.searchFiles(q);
    };

    searchInput?.addEventListener('keydown', (e) => { if (e.key === 'Enter') triggerSearch(); });
    searchBtn?.addEventListener('click', triggerSearch);
  }

  async loadDirectory(path = '.') {
    this.currentPath = path;
    const body = document.getElementById('file-list-body');
    if (!body) return;

    try {
      const resp = await fetch(`/api/ide?root=${encodeURIComponent(path)}`);
      const data = await resp.json();
      const files = data.file_tree || [];

      if (!files.length) {
        body.innerHTML = `<div style="padding:16px;color:var(--text-muted)">Empty directory.</div>`;
        return;
      }

      body.innerHTML = files.map(f => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-radius:var(--radius-sm);cursor:pointer;" class="tree-node" onclick="window.__openFileInIDE('${f.path}')">
          <span style="font-family:var(--font-mono);font-size:12px;display:flex;align-items:center;gap:8px;">
            <i class="fa-solid ${f.is_dir ? 'fa-folder' : 'fa-file-code'}" style="color:${f.is_dir ? 'var(--accent-amber)' : 'var(--accent-cyan)'}"></i>
            <strong>${f.name}</strong>
          </span>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:11px;color:var(--text-muted);font-family:var(--font-mono);">${f.path}</span>
            <button class="icon-btn" title="Copy Path" onclick="event.stopPropagation();navigator.clipboard.writeText('${f.path}');window.alert('Copied path: ${f.path}');" style="width:20px;height:20px;font-size:10px;"><i class="fa-solid fa-copy"></i></button>
            <button class="icon-btn" title="Delete" onclick="event.stopPropagation();if(confirm('Delete ${f.name}?')){fetch('/api/ide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'run_command',command:'rm -rf \\'${f.path}\\''})}).then(()=>window.__refreshFileExplorer());}" style="width:20px;height:20px;font-size:10px;color:var(--accent-red)"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
      `).join('');

      window.__refreshFileExplorer = () => this.loadDirectory(this.currentPath);

      window.__openFileInIDE = (filePath) => {
        if (window.__mitchellStudioController) {
          window.__mitchellStudioController.activatePanel('ide');
          if (window.__mitchellStudioController.ideComponent) {
            window.__mitchellStudioController.ideComponent.openFile(filePath);
          }
        }
      };
    } catch (e) {
      body.innerHTML = `<div style="padding:16px;color:var(--accent-red)">Error reading directory: ${e.message}</div>`;
    }
  }

  async searchFiles(query) {
    const resultsContainer = document.getElementById('file-search-results');
    if (!resultsContainer) return;

    resultsContainer.style.display = 'block';
    resultsContainer.innerHTML = `
      <div style="padding:12px;background:var(--bg-elevated);border:1px solid var(--glass-border);border-radius:var(--radius-md);font-size:12px;color:var(--accent-cyan);">
        <i class="fa-solid fa-spinner fa-spin"></i> Grepping files for "${query}"...
      </div>
    `;

    try {
      const resp = await fetch('/api/files/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query }),
      });
      const data = await resp.json();
      const matches = data.matches || [];

      if (!matches.length) {
        resultsContainer.innerHTML = `
          <div style="padding:12px;background:var(--bg-elevated);border:1px solid var(--glass-border);border-radius:var(--radius-md);font-size:12px;color:var(--text-muted);">
            No matching lines found for "${query}".
          </div>
        `;
        return;
      }

      resultsContainer.innerHTML = `
        <div style="background:var(--bg-surface);border:1px solid var(--glass-border-h);border-radius:var(--radius-lg);padding:14px;">
          <div style="font-weight:700;font-size:12px;margin-bottom:8px;color:var(--accent-mint);">
            Found ${matches.length} matching files for "${query}":
          </div>
          <div style="display:flex;flex-direction:column;gap:8px;">
            ${matches.map(m => `
              <div style="background:var(--bg-elevated);border:1px solid var(--glass-border);border-radius:var(--radius-sm);padding:8px 12px;cursor:pointer;" onclick="window.__openFileInIDE('${m.full_path}')">
                <div style="font-weight:600;font-size:12px;color:var(--accent-cyan);display:flex;justify-content:space-between;">
                  <span><i class="fa-solid fa-file-code"></i> ${m.file}</span>
                  <span style="font-size:10.5px;color:var(--text-muted)">Click to Open in IDE</span>
                </div>
                ${(m.lines || []).map(l => `
                  <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-secondary);margin-top:2px;">
                    <span style="color:var(--accent-amber)">Line ${l.line}:</span> ${l.content}
                  </div>
                `).join('')}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } catch (e) {
      resultsContainer.innerHTML = `<div style="padding:12px;color:var(--accent-red)">Search error: ${e.message}</div>`;
    }
  }
}
