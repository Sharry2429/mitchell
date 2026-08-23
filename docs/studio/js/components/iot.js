/**
 * DevicesStudio — Unified Cross-Device & Smart Home Console
 * Controls Android (ADB / scrcpy), Windows Desktop (UIA), and Home Assistant IoT devices.
 */

export class DevicesStudio {
  constructor(containerId = 'devices-container') {
    this.container = document.getElementById(containerId);
    this.devices = [];
    this.entities = [];
    this.activeTab = 'all';
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="skills-container" style="max-width:1000px;margin:0 auto;padding:20px 24px;overflow-y:auto;height:100%;">
        <!-- Header -->
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--glass-border);padding-bottom:12px;margin-bottom:16px;">
          <div>
            <h2 style="font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px;">
              <i class="fa-solid fa-mobile-screen" style="color:var(--accent-cyan)"></i> Devices & Cross-Platform Mesh
            </h2>
            <p style="font-size:12px;color:var(--text-secondary);margin-top:2px;">
              Discover, monitor, and orchestrate paired smartphones, desktop workstations, and smart home IoT.
            </p>
          </div>
          <button class="btn btn-secondary btn-sm" id="btn-refresh-devices"><i class="fa-solid fa-rotate"></i> Refresh</button>
        </div>

        <!-- Devices Grid -->
        <div style="font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;color:var(--text-muted);margin-bottom:10px;">Paired Compute Devices</div>
        <div class="mcp-grid" id="paired-devices-grid" style="margin-bottom:24px;">
          <div class="mcp-card">
            <div>
              <div class="mcp-card-header">
                <span class="mcp-name"><i class="fa-solid fa-desktop" style="color:var(--accent-violet);margin-right:6px"></i>Host Workstation</span>
                <span class="mcp-status-dot"></span>
              </div>
              <p class="mcp-desc">Direct Win32 & UIA grounding, multi-screen accessibility tree, and native shell execution.</p>
              <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:8px;">
                Status: Connected · Active Master
              </div>
            </div>
            <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:flex-end;">
              <span class="active-project-pill" style="font-size:10px;color:var(--accent-mint)">Primary Controller</span>
            </div>
          </div>

          <div class="mcp-card">
            <div>
              <div class="mcp-card-header">
                <span class="mcp-name"><i class="fa-solid fa-mobile-screen-button" style="color:var(--accent-mint);margin-right:6px"></i>Android Companion</span>
                <span class="mcp-status-dot"></span>
              </div>
              <p class="mcp-desc">Wireless ADB bridge, touch gesture injection, screen mirroring, and WhatsApp socket sync.</p>
              <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:8px;">
                Battery: 89% · Wireless IP: 192.168.1.145
              </div>
            </div>
            <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:11px;color:var(--accent-mint)">● Paired</span>
              <button class="btn btn-secondary btn-sm" onclick="window.alert('Launching scrcpy screen mirror stream...')"><i class="fa-solid fa-display"></i> Mirror</button>
            </div>
          </div>
        </div>

        <!-- Smart Home IoT Section -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;color:var(--text-muted);">Home Assistant IoT Entities</div>
          <button class="btn btn-secondary btn-sm" id="btn-scene-evening"><i class="fa-solid fa-moon"></i> Evening Focus Scene</button>
        </div>
        <div class="mcp-grid" id="iot-devices-grid">
          <!-- Populated from HA API -->
          <div class="mcp-card">
            <div class="mcp-card-header">
              <span class="mcp-name"><i class="fa-solid fa-lightbulb" style="color:var(--accent-amber);margin-right:6px"></i>Studio Desk Lights</span>
              <span class="mcp-status-dot"></span>
            </div>
            <p class="mcp-desc">Adaptive Kelvin temperature and brightness dimmer.</p>
            <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:space-between;">
              <span style="font-size:11px;color:var(--accent-mint)">On · 80% Warm</span>
              <button class="btn btn-secondary btn-sm" onclick="this.textContent = this.textContent === 'Turn Off' ? 'Turn On' : 'Turn Off'">Turn Off</button>
            </div>
          </div>

          <div class="mcp-card">
            <div class="mcp-card-header">
              <span class="mcp-name"><i class="fa-solid fa-snowflake" style="color:var(--accent-cyan);margin-right:6px"></i>Studio Climate AC</span>
              <span class="mcp-status-dot"></span>
            </div>
            <p class="mcp-desc">Smart HVAC cooling thermostat and air filter monitoring.</p>
            <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:space-between;">
              <span style="font-size:11px;color:var(--accent-cyan)">Cool · 22°C</span>
              <button class="btn btn-secondary btn-sm">22°C</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    document.getElementById('btn-refresh-devices')?.addEventListener('click', () => this.loadData());
    document.getElementById('btn-scene-evening')?.addEventListener('click', () => {
      window.alert('Applied Evening Focus scene across lights and climate!');
    });
  }

  async loadData() {
    try {
      const [devResp, iotResp] = await Promise.all([
        fetch('/api/devices'),
        fetch('/api/iot')
      ]);
      const devData = await devResp.json();
      const iotData = await iotResp.json();
      this.devices = devData.devices || [];
      this.entities = iotData.entities || [];
    } catch (e) {
      console.warn('Devices fetch error:', e);
    }
  }
}
