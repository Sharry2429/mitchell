/**
 * Native Document Workspace Component
 * Handles rich document drafting, split live markdown preview, section outlines, and AI report generation.
 */

export class DocumentsStudio {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.activeDoc = null;
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="docs-studio-wrapper">
        <!-- Studio Header Toolbar -->
        <div class="docs-toolbar">
          <div class="docs-toolbar-left">
            <span class="docs-title"><i class="fa-solid fa-file-lines" style="color:var(--accent-purple);margin-right:6px"></i>Document Studio</span>
            <input type="text" id="doc-title-input" class="doc-title-input" value="Untitled Document" placeholder="Document Title..." />
          </div>
          <div class="docs-toolbar-actions">
            <button class="btn btn-secondary btn-sm" id="doc-btn-new" title="New Document"><i class="fa-solid fa-file-circle-plus"></i> New</button>
            <button class="btn btn-secondary btn-sm" id="doc-btn-generate-ai" title="Mitchell AI Report Generator"><i class="fa-solid fa-wand-magic-sparkles" style="color:var(--accent-purple)"></i> Generate Report</button>
            <button class="btn btn-secondary btn-sm" id="doc-btn-export-html" title="Export HTML"><i class="fa-solid fa-download"></i> Export</button>
            <button class="btn btn-primary btn-sm" id="doc-btn-save" title="Save Document"><i class="fa-solid fa-floppy-disk"></i> Save</button>
          </div>
        </div>

        <!-- Split Layout: Document List / Outline + Editor + Live Preview -->
        <div class="docs-split-view">
          <!-- Left Sidebar: Document List -->
          <div class="docs-sidebar">
            <div class="docs-sidebar-header">
              <span>MY DOCUMENTS</span>
              <button class="icon-btn-sm" id="docs-refresh-btn"><i class="fa-solid fa-rotate"></i></button>
            </div>
            <div class="docs-list" id="docs-list-container">
              <div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading documents...</div>
            </div>
          </div>

          <!-- Center: Markdown Editor -->
          <div class="docs-editor-pane">
            <div class="docs-pane-header">
              <span><i class="fa-solid fa-pen-to-square"></i> Markdown Editor</span>
              <span class="word-count" id="doc-word-count">0 words</span>
            </div>
            <textarea id="doc-markdown-input" class="docs-textarea" placeholder="# Enter document content or ask Mitchell to generate a report..."></textarea>
          </div>

          <!-- Right: Live Formatted Preview -->
          <div class="docs-preview-pane">
            <div class="docs-pane-header">
              <span><i class="fa-solid fa-eye"></i> Formatted Preview</span>
            </div>
            <div class="docs-preview-content" id="doc-preview-content">
              <div class="empty-state"><p>Live preview will appear as you type.</p></div>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadDocumentList();
  }

  bindEvents() {
    const markdownInput = document.getElementById('doc-markdown-input');
    markdownInput?.addEventListener('input', () => this.updatePreview());

    document.getElementById('docs-refresh-btn')?.addEventListener('click', () => this.loadDocumentList());
    document.getElementById('doc-btn-new')?.addEventListener('click', () => this.createNewDocument());
    document.getElementById('doc-btn-save')?.addEventListener('click', () => this.saveActiveDocument());
    document.getElementById('doc-btn-generate-ai')?.addEventListener('click', () => this.promptGenerateReport());
    document.getElementById('doc-btn-export-html')?.addEventListener('click', () => this.exportHtml());
  }

  async loadDocumentList() {
    const listContainer = document.getElementById('docs-list-container');
    try {
      const resp = await fetch('/api/documents');
      const data = await resp.json();
      const docs = data.documents || [];

      if (!docs.length) {
        listContainer.innerHTML = `
          <div class="empty-state" style="padding:16px;">
            <p>No documents yet.</p>
            <button class="btn btn-secondary btn-sm" id="docs-quick-scaffold">Generate Sample Report</button>
          </div>
        `;
        document.getElementById('docs-quick-scaffold')?.addEventListener('click', () => {
          this.generateReport('Autonomous Agent Performance Q3');
        });
        return;
      }

      let html = '';
      for (const d of docs) {
        html += `
          <div class="doc-list-item" data-id="${d.id}">
            <div class="doc-item-title"><i class="fa-solid fa-file-lines" style="color:var(--accent-purple);margin-right:6px"></i>${d.title}</div>
            <div class="doc-item-meta">${d.size_bytes} bytes • ${d.updated_at ? new Date(d.updated_at).toLocaleDateString() : 'recent'}</div>
          </div>
        `;
      }
      listContainer.innerHTML = html;

      // Bind item clicks
      document.querySelectorAll('.doc-list-item').forEach(el => {
        el.addEventListener('click', () => this.loadDocument(el.dataset.id));
      });

      // Auto-load first document if none active
      if (!this.activeDoc && docs.length > 0) {
        this.loadDocument(docs[0].id);
      }
    } catch (e) {
      listContainer.innerHTML = `<div class="empty-state"><p>Error: ${e.message}</p></div>`;
    }
  }

  async loadDocument(docId) {
    try {
      const resp = await fetch(`/api/documents?id=${docId}`);
      const doc = await resp.json();
      if (doc) {
        this.activeDoc = doc;
        document.getElementById('doc-title-input').value = doc.title;
        document.getElementById('doc-markdown-input').value = doc.content;
        this.updatePreview();

        document.querySelectorAll('.doc-list-item').forEach(i => i.classList.remove('active'));
        document.querySelector(`.doc-list-item[data-id="${docId}"]`)?.classList.add('active');
      }
    } catch (e) {
      console.error('Error loading document:', e);
    }
  }

  updatePreview() {
    const input = document.getElementById('doc-markdown-input');
    const preview = document.getElementById('doc-preview-content');
    const wordCount = document.getElementById('doc-word-count');

    const text = input.value;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    if (wordCount) wordCount.textContent = `${words} words`;

    if (!text.trim()) {
      preview.innerHTML = '<div class="empty-state"><p>Live preview will appear as you type.</p></div>';
      return;
    }

    // High quality markdown rendering
    let html = text
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*([^*]+)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/gim, '<em>$1</em>')
      .replace(/```(\w*)\n([\s\S]*?)```/gim, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
      .replace(/^\- (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br>');

    preview.innerHTML = `<div class="rendered-markdown"><p>${html}</p></div>`;
  }

  createNewDocument() {
    this.activeDoc = null;
    document.getElementById('doc-title-input').value = 'New Document';
    document.getElementById('doc-markdown-input').value = '# New Document\n\nWrite your content here...\n';
    this.updatePreview();
  }

  async saveActiveDocument() {
    const title = document.getElementById('doc-title-input').value.trim() || 'Untitled Document';
    const content = document.getElementById('doc-markdown-input').value;
    const docId = this.activeDoc ? this.activeDoc.doc_id : title.toLowerCase().replace(/[^a-z0-9]+/g, '_');

    try {
      const resp = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'save',
          doc_id: docId,
          title: title,
          content: content,
        }),
      });
      const data = await resp.json();
      if (data.status === 'saved') {
        await this.loadDocumentList();
      }
    } catch (e) {
      alert(`Failed to save: ${e.message}`);
    }
  }

  promptGenerateReport() {
    const topic = prompt('Enter report topic (e.g. "Q3 Architecture Benchmark" or "Multi-Agent System Health"):');
    if (topic) {
      this.generateReport(topic);
    }
  }

  async generateReport(topic) {
    const preview = document.getElementById('doc-preview-content');
    preview.innerHTML = '<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Mitchell is generating your executive report...</div>';

    try {
      const resp = await fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'generate_report',
          topic: topic,
        }),
      });
      const data = await resp.json();
      if (data.document) {
        this.activeDoc = data.document;
        document.getElementById('doc-title-input').value = data.document.title;
        document.getElementById('doc-markdown-input').value = data.document.content;
        this.updatePreview();
        await this.loadDocumentList();
      }
    } catch (e) {
      alert(`Report generation error: ${e.message}`);
    }
  }

  exportHtml() {
    const title = document.getElementById('doc-title-input').value || 'Document';
    const preview = document.getElementById('doc-preview-content').innerHTML;

    const fullHtml = `<!DOCTYPE html><html><head><title>${title}</title><style>body{font-family:system-ui;max-width:800px;margin:40px auto;line-height:1.6;color:#222;padding:0 20px;}</style></head><body>${preview}</body></html>`;

    const blob = new Blob([fullHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.html`;
    a.click();
  }
}
