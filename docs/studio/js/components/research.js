/**
 * Perplexity-Style Deep Research Frontend Component
 * Features multi-query generation, live source card stream, synthesized answer with interactive citation pills [1], [2],
 * and one-click "Save to Documents" workflow.
 */

export class DeepResearchStudio {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.currentResult = null;
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="research-wrapper">
        <!-- Research Search Bar -->
        <div class="research-hero">
          <div class="research-hero-title">
            <i class="fa-solid fa-magnifying-glass-chart" style="color:var(--accent-purple);margin-right:8px"></i>
            Autonomous Deep Researcher
          </div>
          <div class="research-hero-subtitle">Perplexity-style multi-step research, real-environment web verification, and citation synthesis.</div>
          <div class="research-input-bar">
            <i class="fa-solid fa-sparkles research-sparkle"></i>
            <input type="text" id="research-query-input" placeholder="Ask anything to research across live web & technical papers..." autocomplete="off" />
            <button class="btn btn-primary" id="research-submit-btn"><i class="fa-solid fa-arrow-right"></i> Research</button>
          </div>
        </div>

        <!-- Research Results Area -->
        <div class="research-results-container" id="research-results-container">
          <div class="empty-state">
            <i class="fa-solid fa-book-open-reader"></i>
            <p>Enter a research query above to begin automated web synthesis with live citations.</p>
            <div class="quick-research-prompts">
              <button class="chip-prompt" data-query="Real-world Chrome profile CDP automation benchmarks">Real Chrome CDP Profile Automation</button>
              <button class="chip-prompt" data-query="Munder-Difflin multi-agent coding harness architecture">Munder-Difflin Coding Harness</button>
              <button class="chip-prompt" data-query="Home Assistant REST & WebSocket IoT telemetry standards">Home Assistant IoT Standards</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const input = document.getElementById('research-query-input');
    const submitBtn = document.getElementById('research-submit-btn');

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = input.value.trim();
        if (query) this.executeResearch(query);
      }
    });

    submitBtn?.addEventListener('click', () => {
      const query = input.value.trim();
      if (query) this.executeResearch(query);
    });

    document.querySelectorAll('.chip-prompt').forEach(chip => {
      chip.addEventListener('click', () => {
        const q = chip.dataset.query;
        if (input) input.value = q;
        this.executeResearch(q);
      });
    });
  }

  async executeResearch(query) {
    const container = document.getElementById('research-results-container');
    container.innerHTML = `
      <div class="research-loading-state">
        <div class="research-progress-header">
          <div class="spinner-pulse"><i class="fa-solid fa-compass fa-spin" style="color:var(--accent-purple)"></i></div>
          <div class="progress-text">
            <h4>Deep Research in Progress...</h4>
            <p id="research-status-step">1/3 Decomposing research goals & searching live web sources...</p>
          </div>
        </div>
      </div>
    `;

    try {
      const resp = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, max_sources: 4 }),
      });
      const data = await resp.json();
      this.currentResult = data;
      this.renderResults(data);
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><p>Research error: ${e.message}</p></div>`;
    }
  }

  renderResults(data) {
    const container = document.getElementById('research-results-container');

    // Sources cards
    const sourcesHtml = (data.sources || []).map(s => `
      <a href="${s.url}" target="_blank" class="research-source-card" title="${s.url}">
        <div class="source-header">
          <span class="source-pill">[${s.index}]</span>
          <span class="source-domain">${s.domain}</span>
        </div>
        <div class="source-title">${s.title}</div>
        <div class="source-snippet">${s.snippet}</div>
      </a>
    `).join('');

    // Key findings
    const findingsHtml = (data.key_findings || []).map(f => `
      <li class="finding-item"><i class="fa-solid fa-check" style="color:var(--accent-green);margin-right:6px"></i>${f}</li>
    `).join('');

    // Detailed report formatted
    const formattedReport = (data.detailed_report || '')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/\[(\d+)\]/gim, '<span class="citation-pill">[$1]</span>')
      .replace(/\*\*([^*]+)\*\*/gim, '<strong>$1</strong>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br>');

    container.innerHTML = `
      <div class="research-complete-layout">
        <!-- Sources Horizontal Scroll Carousel -->
        <div class="research-section-title"><i class="fa-solid fa-globe"></i> Verified Sources (${data.sources?.length || 0})</div>
        <div class="research-sources-carousel">${sourcesHtml}</div>

        <!-- Executive Key Findings -->
        <div class="research-card findings-card">
          <div class="research-card-title"><i class="fa-solid fa-lightbulb" style="color:var(--accent-yellow)"></i> Key Takeaways</div>
          <ul class="findings-list">${findingsHtml}</ul>
        </div>

        <!-- Synthesized Report -->
        <div class="research-card synthesis-card">
          <div class="synthesis-header">
            <div class="research-card-title"><i class="fa-solid fa-file-invoice" style="color:var(--accent-purple)"></i> Comprehensive Synthesis</div>
            <button class="btn btn-secondary btn-sm" id="research-save-doc-btn"><i class="fa-solid fa-file-import"></i> Save as Document</button>
          </div>
          <div class="synthesis-body">
            <p>${formattedReport}</p>
          </div>
        </div>
      </div>
    `;

    document.getElementById('research-save-doc-btn')?.addEventListener('click', async () => {
      try {
        const resp = await fetch('/api/documents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'generate_report',
            topic: data.query,
            content: `# Research Synthesis: ${data.query}\n\n${data.detailed_report}`,
          }),
        });
        const resData = await resp.json();
        alert(`Research successfully saved as Document "${data.query}"!`);
      } catch (e) {
        alert(`Error saving document: ${e.message}`);
      }
    });
  }
}
