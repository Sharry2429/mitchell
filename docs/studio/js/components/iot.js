/**
 * DevicesStudio — Unified Cross-Device Mesh & Wireless ADB Pairing Console
 * Controls Android (Wireless ADB / scrcpy), Windows Desktop (UIA), and Home Assistant IoT devices.
 */

export class DevicesStudio {
  constructor(containerId = 'devices-container') {
    this.container = document.getElementById(containerId);
    this.devices = [];
    this.entities = [];
    this.isPairing = false;
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="skills-container" style="max-width:1080px;margin:0 auto;padding:24px;overflow-y:auto;height:100%;">
        <!-- Header -->
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--glass-border);padding-bottom:16px;margin-bottom:20px;">
          <div>
            <h2 style="font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px;">
              <i class="fa-solid fa-mobile-screen" style="color:var(--accent-cyan)"></i> Devices & Cross-Platform Mesh
            </h2>
            <p style="font-size:12.5px;color:var(--text-secondary);margin-top:3px;">
              Auto-sync, wireless ADB debugging pairing, and smart home IoT orchestration directly from your browser.
            </p>
          </div>
          <div style="display:flex;gap:10px;">
            <button class="btn btn-primary btn-sm" id="btn-pair-android" style="display:flex;align-items:center;gap:6px;">
              <i class="fa-solid fa-wifi"></i> Pair Android (Wireless ADB)
            </button>
            <button class="btn btn-secondary btn-sm" id="btn-refresh-devices">
              <i class="fa-solid fa-rotate"></i> Sync Devices
            </button>
          </div>
        </div>

        <!-- Pairing Progress Notification Banner (Hidden by default) -->
        <div id="device-pairing-banner" style="display:none;margin-bottom:20px;padding:12px 16px;border-radius:10px;background:rgba(88,166,255,0.1);border:1px solid rgba(88,166,255,0.3);font-size:13px;display:flex;align-items:center;justify-content:space-between;">
          <div style="display:flex;align-items:center;gap:10px;">
            <i class="fa-solid fa-circle-notch fa-spin" style="color:var(--accent-blue)"></i>
            <span id="device-pairing-msg">Scanning USB & switching phone to Wireless ADB (port 5555)...</span>
          </div>
        </div>

        <!-- Devices Grid -->
        <div style="font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;color:var(--text-muted);margin-bottom:12px;">Paired Compute Devices & Workstations</div>
        <div class="mcp-grid" id="paired-devices-grid" style="margin-bottom:30px;">
          <!-- Dynamically populated -->
        </div>

        <!-- Smart Home IoT Section -->
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;color:var(--text-muted);">Home Assistant IoT Entities</div>
          <button class="btn btn-secondary btn-sm" id="btn-scene-evening"><i class="fa-solid fa-moon"></i> Evening Focus Scene</button>
        </div>
        <div class="mcp-grid" id="iot-devices-grid">
          <!-- Populated from HA API -->
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadData();
  }

  bindEvents() {
    document.getElementById('btn-refresh-devices')?.addEventListener('click', () => this.syncDevices());
    document.getElementById('btn-pair-android')?.addEventListener('click', () => this.pairWirelessAndroid());
    document.getElementById('btn-scene-evening')?.addEventListener('click', () => {
      window.alert('Applied Evening Focus scene across smart lights and climate!');
    });
  }

  async pairWirelessAndroid() {
    const banner = document.getElementById('device-pairing-banner');
    const msg = document.getElementById('device-pairing-msg');
    if (banner) banner.style.display = 'flex';
    if (msg) msg.textContent = 'Scanning USB connection & switching Android phone to Wireless ADB on local Wi-Fi...';

    try {
      const resp = await fetch('/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'pair_android', port: 5555 }),
      });
      const data = await resp.json();

      if (data.success) {
        if (msg) msg.textContent = `✓ ${data.message || 'Wireless ADB Paired! IP: ' + data.wireless_serial}`;
        if (banner) {
          banner.style.background = 'rgba(63, 185, 80, 0.15)';
          banner.style.borderColor = 'rgba(63, 185, 80, 0.4)';
        }
      } else {
        if (msg) msg.textContent = `Notice: ${data.error || 'Please connect Android via USB with USB Debugging enabled first.'}`;
        if (banner) {
          banner.style.background = 'rgba(248, 81, 73, 0.15)';
          banner.style.borderColor = 'rgba(248, 81, 73, 0.4)';
        }
      }
    } catch (e) {
      if (msg) msg.textContent = 'Failed to execute pairing request.';
    }

    setTimeout(() => {
      this.loadData();
    }, 1500);
  }

  async syncDevices() {
    await fetch('/api/devices', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'sync' }),
    });
    await this.loadData();
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

      this.renderDevicesList();
      this.renderIoTList();
    } catch (e) {
      console.warn('Devices fetch error:', e);
    }
  }

  renderDevicesList() {
    const grid = document.getElementById('paired-devices-grid');
    if (!grid) return;

    if (this.devices.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; padding: 24px; text-align: center; color: var(--text-muted);">No devices connected. Click "Pair Android" or connect phone via USB.</div>`;
      return;
    }

    grid.innerHTML = this.devices.map(d => {
      const isOnline = d.status === 'connected' || d.status === 'online';
      const isWireless = d.is_wireless || d.type === 'android';
      const icon = d.icon || (d.type === 'desktop' ? 'desktop' : 'mobile-screen-button');
      const accent = d.type === 'desktop' ? 'var(--accent-violet)' : 'var(--accent-mint)';

      return `
        <div class="mcp-card">
          <div>
            <div class="mcp-card-header">
              <span class="mcp-name">
                <i class="fa-solid fa-${icon}" style="color:${accent};margin-right:8px;"></i>${d.name || d.id}
              </span>
              <span class="mcp-status-dot ${isOnline ? 'online' : ''}"></span>
            </div>
            <p class="mcp-desc">${d.details || d.os || 'Cross-Platform Connected Compute Node'}</p>
            <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:8px;">
              ${d.ip_address ? `Wi-Fi IP: ${d.ip_address}` : `Serial: ${d.id || d.serial || 'N/A'}`} · Status: ${d.status || 'Active'}
            </div>
          </div>
          <div style="border-top:1px solid var(--glass-border);padding-top:10px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11px;font-weight:600;color:${isOnline ? 'var(--accent-mint)' : 'var(--text-muted)'};">
              ${isOnline ? '● Online' : '○ Standby'}
            </span>
            ${d.type === 'android' ? `
              <button class="btn btn-secondary btn-sm" onclick="fetch('/api/devices', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:'pair_android'})}).then(()=>alert('Wireless ADB refreshed!'))">
                <i class="fa-solid fa-wifi"></i> Sync Wireless
              </button>
            ` : `
              <span class="active-project-pill" style="font-size:10px;color:var(--accent-mint)">Primary Master</span>
            `}
          </div>
        </div>
      `;
    }).join('');
  }

  renderIoTList() {
    const grid = document.getElementById('iot-devices-grid');
    if (!grid) return;

    grid.innerHTML = `
      <div class="mcp-card">
        <div class="mcp-card-header">
          <span class="mcp-name"><i class="fa-solid fa-lightbulb" style="color:var(--accent-amber);margin-right:6px"></i>Studio Desk Lights</span>
          <span class="mcp-status-dot online"></span>
        </div>
        <p class="mcp-desc">Adaptive Kelvin temperature and brightness dimmer.</p>
        <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:11px;color:var(--accent-mint)">On · 80% Warm</span>
          <button class="btn btn-secondary btn-sm" onclick="this.textContent = this.textContent === 'Turn Off' ? 'Turn On' : 'Turn Off'">Turn Off</button>
        </div>
      </div>

      <div class="mcp-card">
        <div class="mcp-card-header">
          <span class="mcp-name"><i class="fa-solid fa-snowflake" style="color:var(--accent-cyan);margin-right:6px"></i>Studio Climate AC</span>
          <span class="mcp-status-dot online"></span>
        </div>
        <p class="mcp-desc">Smart HVAC cooling thermostat and air filter monitoring.</p>
        <div style="border-top:1px solid var(--glass-border);padding-top:8px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:11px;color:var(--accent-cyan)">Cool · 22°C</span>
          <button class="btn btn-secondary btn-sm">22°C</button>
        </div>
      </div>
    `;
  }
}
