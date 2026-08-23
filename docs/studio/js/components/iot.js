/**
 * Home Assistant Smart Home & IoT Component
 * Direct device cards (lights, switches, climate, locks, scenes) with real-time state toggles.
 */

export class SmartHomeStudio {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.entities = [];
  }

  async render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="iot-wrapper">
        <!-- IoT Header -->
        <div class="iot-header">
          <div class="iot-header-left">
            <span class="iot-title"><i class="fa-solid fa-house-signal" style="color:var(--accent-cyan);margin-right:8px"></i>Smart Home & IoT Hub</span>
            <span class="badge badge-green" id="iot-status-badge">Home Assistant Ready</span>
          </div>
          <div class="iot-header-actions">
            <button class="btn btn-secondary btn-sm" id="iot-refresh-btn"><i class="fa-solid fa-rotate"></i> Refresh</button>
            <button class="btn btn-secondary btn-sm" id="iot-scene-focus"><i class="fa-solid fa-moon"></i> Focus Scene</button>
          </div>
        </div>

        <!-- Entity Filter Tabs -->
        <div class="memory-tabs iot-tabs">
          <button class="tab-btn active" data-filter="all">All Devices</button>
          <button class="tab-btn" data-filter="light">Lights</button>
          <button class="tab-btn" data-filter="climate">Climate</button>
          <button class="tab-btn" data-filter="lock">Locks</button>
          <button class="tab-btn" data-filter="switch">Switches</button>
        </div>

        <!-- Devices Grid -->
        <div class="iot-grid" id="iot-grid-container">
          <div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading IoT entity states...</div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadEntities();
  }

  bindEvents() {
    document.getElementById('iot-refresh-btn')?.addEventListener('click', () => this.loadEntities());

    document.getElementById('iot-scene-focus')?.addEventListener('click', async () => {
      await this.callService('light', 'turn_off', 'light.living_room');
      await this.callService('climate', 'set_temperature', 'climate.home_ac', { temperature: 21 });
      this.loadEntities();
    });

    document.querySelectorAll('.iot-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.iot-tabs .tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.renderGrid(btn.dataset.filter);
      });
    });
  }

  async loadEntities() {
    const grid = document.getElementById('iot-grid-container');
    try {
      const resp = await fetch('/api/iot');
      const data = await resp.json();
      this.entities = data.entities || [];
      this.renderGrid('all');
    } catch (e) {
      grid.innerHTML = `<div class="empty-state"><p>Error loading IoT devices: ${e.message}</p></div>`;
    }
  }

  renderGrid(filter = 'all') {
    const grid = document.getElementById('iot-grid-container');
    const filtered = filter === 'all'
      ? this.entities
      : this.entities.filter(e => e.entity_id.startsWith(filter));

    if (!filtered.length) {
      grid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-house-signal"></i><p>No devices matching this filter.</p></div>';
      return;
    }

    let html = '';
    for (const e of filtered) {
      const [domain] = e.entity_id.split('.');
      const isOn = e.state === 'on' || e.state === 'cool' || e.state === 'locked';
      const icon = this.getDomainIcon(domain);
      const friendlyName = e.attributes?.friendly_name || e.entity_id;

      html += `
        <div class="iot-device-card ${isOn ? 'active' : ''}" data-entity="${e.entity_id}">
          <div class="iot-card-top">
            <div class="iot-icon-box ${isOn ? 'active' : ''}">
              <i class="${icon}"></i>
            </div>
            <label class="switch">
              <input type="checkbox" class="iot-toggle" data-entity="${e.entity_id}" data-domain="${domain}" ${isOn ? 'checked' : ''} />
              <span class="slider round"></span>
            </label>
          </div>
          <div class="iot-card-name">${friendlyName}</div>
          <div class="iot-card-state">State: <strong>${e.state.toUpperCase()}</strong></div>
        </div>
      `;
    }

    grid.innerHTML = html;

    // Bind toggle switches
    document.querySelectorAll('.iot-toggle').forEach(chk => {
      chk.addEventListener('change', async () => {
        const entity = chk.dataset.entity;
        const domain = chk.dataset.domain;
        const service = chk.checked ? 'turn_on' : 'turn_off';
        await this.callService(domain, service, entity);
        // Refresh local state visually
        const card = chk.closest('.iot-device-card');
        if (card) {
          card.classList.toggle('active', chk.checked);
          const stateText = card.querySelector('.iot-card-state');
          if (stateText) stateText.innerHTML = `State: <strong>${chk.checked ? 'ON' : 'OFF'}</strong>`;
        }
      });
    });
  }

  getDomainIcon(domain) {
    switch (domain) {
      case 'light': return 'fa-solid fa-lightbulb';
      case 'climate': return 'fa-solid fa-snowflake';
      case 'lock': return 'fa-solid fa-lock';
      case 'switch': return 'fa-solid fa-power-off';
      case 'camera': return 'fa-solid fa-video';
      default: return 'fa-solid fa-plug';
    }
  }

  async callService(domain, service, entityId, data = {}) {
    try {
      await fetch('/api/iot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: domain,
          service: service,
          entity_id: entityId,
          service_data: data,
        }),
      });
    } catch (e) {
      console.error('Error calling IoT service:', e);
    }
  }
}
