/**
 * AllEars Sound Tracker — Full Dashboard Custom Card
 * Lovelace Web Component | Vanilla JS | Uses HA CSS Variables Only
 */

const DOMAIN = 'allears';

class AllEarsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = null;
    this._initialized = false;
    this._activeTab = 'overview';
    this._settings = {
      notifications: true,
      soundAlerts: false,
      logEvents: true,
    };
    this._activityLog = [];
  }

  static getStubConfig() {
    return {
      type: "custom:all-ears-card",
      device_name: "AllEars Sound Tracker",
      location: "Living Room",
      firmware: "1.0.0",
      notifications: true,
      soundAlerts: false,
      logEvents: true
    };
  }

  // ─── Lovelace lifecycle ──────────────────────────────────────────────────

  setConfig(config) {
    this._config = {
      device_name: 'AllEars Sound Tracker',
      location: 'Living Room',
      firmware: '1.0.0',
      ...config,
    };
    // Derive entity IDs from optional overrides
    const base = config.entity_base || '';
    this._binarySensorId  = config.binary_sensor  || (base + 'binary_sensor.allears_sound_active');
    this._soundSensorId   = config.sound_sensor   || (base + 'sensor.allears_last_detected_sound');
    this._flowSensorId    = config.flow_sensor    || (base + 'sensor.allears_last_triggered_flow');
    // New: select entity for flow filter (auto-registered by Android app)
    this._selectEntityId  = config.select_entity  || (base + 'select.allears_active_flow_filter');
    // Track which flow is selected for activity log filtering
    this._selectedFlow = 'All Flows';
  }

  getCardSize() { return 6; }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;

    if (!this._initialized) {
      this._render();
      this._initialized = true;
    } else {
      this._syncState(prev);
    }
  }

  // ─── State helpers ───────────────────────────────────────────────────────

  get _activeState() {
    const obj = this._hass?.states[this._binarySensorId];
    if (!obj) return 'empty';
    if (obj.state === 'unavailable' || obj.state === 'unknown') return 'unavailable';
    return obj.state === 'on' ? 'active' : 'clear';
  }

  _sensorVal(entityId) {
    const obj = this._hass?.states[entityId];
    if (!obj) return '—';
    if (obj.state === 'unavailable' || obj.state === 'unknown') return 'Unknown';
    return obj.state;
  }

  _sensorAttr(entityId, attr) {
    const obj = this._hass?.states[entityId];
    return obj?.attributes?.[attr] ?? null;
  }

  _callService(service, data = {}) {
    this._hass.callService(DOMAIN, service, data);
  }

  // ─── Initial full render ─────────────────────────────────────────────────

  _render() {
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <div class="ae-root" id="root"></div>
    `;
    this._root = this.shadowRoot.getElementById('root');
    this._buildDOM();
    this._syncState(null);
    this._attachListeners();
  }

  _buildDOM() {
    const state = this._activeState;
    this._root.innerHTML = `
      <!-- ════ HEADER ════ -->
      <div class="ae-header">
        <div class="ae-header-left">
          <div class="ae-header-icon" id="hdr-icon">
            <div class="ae-wave" id="hdr-wave">
              <span></span><span></span><span></span><span></span>
            </div>
            <ha-icon icon="mdi:ear-hearing" id="hdr-ha-icon"></ha-icon>
          </div>
          <div>
            <div class="ae-title">${this._config.device_name}</div>
            <div class="ae-subtitle" id="hdr-sub">${this._config.location} · Firmware ${this._config.firmware}</div>
          </div>
        </div>
        <div class="ae-status-pill" id="hdr-pill">
          <span class="ae-pill-dot" id="hdr-dot"></span>
          <span id="hdr-pill-label">Listening</span>
        </div>
      </div>

      <!-- ════ TAB BAR ════ -->
      <div class="ae-tabs" role="tablist">
        <button class="ae-tab active" data-tab="overview" role="tab" aria-selected="true">Overview</button>
        <button class="ae-tab" data-tab="sensors" role="tab" aria-selected="false">Sensors</button>
        <button class="ae-tab" data-tab="activity" role="tab" aria-selected="false">Activity</button>
        <button class="ae-tab" data-tab="settings" role="tab" aria-selected="false">Settings</button>
      </div>

      <!-- ════ PANELS ════ -->
      <div id="panel-overview" class="ae-panel active">
        ${this._panelOverview()}
      </div>
      <div id="panel-sensors" class="ae-panel">
        ${this._panelSensors()}
      </div>
      <div id="panel-activity" class="ae-panel">
        ${this._panelActivity()}
      </div>
      <div id="panel-settings" class="ae-panel">
        ${this._panelSettings()}
      </div>
    `;
  }

  // ─── Panel HTML factories ────────────────────────────────────────────────

  _panelOverview() {
    return `
      <!-- Sound Monitor card -->
      <div class="ae-card ae-monitor-card">
        <div class="ae-monitor-top">
          <div>
            <div class="ae-monitor-title">Sound Monitor</div>
            <div class="ae-monitor-meta" id="mon-meta">${this._config.location} · Always active</div>
          </div>
          <div class="ae-badge">AllEars v${this._config.firmware}</div>
        </div>
        <div class="ae-monitor-bottom">
          <span class="ae-label">Last detected sound</span>
          <span class="ae-monitor-sound" id="mon-sound">Listening...</span>
        </div>
      </div>

      <!-- Flow Filter + Sensors -->
      <div class="ae-card">
        <div class="ae-section-label">ACTIVE FLOW FILTER</div>
        <div class="ae-flow-filter-wrap">
          <ha-icon icon="mdi:waves" class="ae-flow-icon"></ha-icon>
          <select class="ae-flow-select" id="flow-select">
            <option value="All Flows">All Flows</option>
          </select>
          <span class="ae-flow-hint" id="flow-hint"></span>
        </div>
        <div class="ae-section-label" style="margin-top:16px">SENSORS</div>
        <div class="ae-sensor-grid" id="ov-sensor-grid">
          ${this._sensorTile('mdi:microphone', 'Last detected sound', this._sensorVal(this._soundSensorId), 'ov-sound-val')}
          ${this._sensorTile('mdi:waves', 'Last triggered flow', this._sensorVal(this._flowSensorId), 'ov-flow-val')}
          ${this._sensorTile('mdi:ear-hearing', 'Sound active', 'Clear', 'ov-active-val', true)}
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="ae-card">
        <div class="ae-section-label">QUICK ACTIONS</div>
        <div class="ae-action-grid">
          <div class="ae-action-tile" id="qa-automations">
            <ha-icon icon="mdi:lightning-bolt" class="ae-action-icon"></ha-icon>
            <div class="ae-action-name">Automations</div>
            <div class="ae-action-sub">AllEars trigger</div>
            <button class="ae-add-btn" data-action="automation">+ Add</button>
          </div>
          <div class="ae-action-tile" id="qa-scenes">
            <ha-icon icon="mdi:image-multiple" class="ae-action-icon"></ha-icon>
            <div class="ae-action-name">Scenes</div>
            <div class="ae-action-sub">Link a scene</div>
            <button class="ae-add-btn" data-action="scene">+ Add</button>
          </div>
          <div class="ae-action-tile" id="qa-scripts">
            <ha-icon icon="mdi:script-text" class="ae-action-icon"></ha-icon>
            <div class="ae-action-name">Scripts</div>
            <div class="ae-action-sub">Run a script</div>
            <button class="ae-add-btn" data-action="script">+ Add</button>
          </div>
        </div>
      </div>
    `;
  }

  _sensorTile(icon, label, value, id, isActive = false) {
    return `
      <div class="ae-sensor-tile${isActive ? ' ae-tile-clear' : ''}" id="${id}-tile">
        <div class="ae-sensor-icon-wrap">
          <ha-icon icon="${icon}"></ha-icon>
        </div>
        <div class="ae-sensor-label">${label}</div>
        <div class="ae-sensor-value" id="${id}">${value}</div>
      </div>
    `;
  }

  _panelSensors() {
    return `
      <!-- Detail sensor cards -->
      <div class="ae-card ae-sensor-detail-card" id="sd-sound">
        <div class="ae-sensor-detail-header">
          <div class="ae-sensor-detail-icon-wrap blue">
            <ha-icon icon="mdi:microphone"></ha-icon>
          </div>
          <div>
            <div class="ae-label">SOUND DETECTED</div>
            <div class="ae-sensor-detail-value" id="sd-sound-val">${this._sensorVal(this._soundSensorId)}</div>
          </div>
        </div>
      </div>

      <div class="ae-card ae-sensor-detail-card" id="sd-flow">
        <div class="ae-sensor-detail-header">
          <div class="ae-sensor-detail-icon-wrap amber">
            <ha-icon icon="mdi:waves"></ha-icon>
          </div>
          <div>
            <div class="ae-label">FLOW TRIGGERED</div>
            <div class="ae-sensor-detail-value" id="sd-flow-val">${this._sensorVal(this._flowSensorId)}</div>
          </div>
        </div>
      </div>

      <div class="ae-card ae-sensor-detail-card">
        <div class="ae-sensor-detail-header">
          <div class="ae-sensor-detail-icon-wrap green" id="sd-active-wrap">
            <ha-icon icon="mdi:ear-hearing"></ha-icon>
          </div>
          <div>
            <div class="ae-label">SOUND ACTIVE</div>
            <div class="ae-sensor-detail-value" id="sd-active-val">Clear</div>
          </div>
        </div>
        <div class="ae-sensor-attrs">
          <div class="ae-attr-row"><span class="ae-label">ENTITY</span><span>${this._binarySensorId}</span></div>
        </div>
      </div>
    `;
  }

  _panelActivity() {
    return `
      <!-- Device card -->
      <div class="ae-card">
        <div class="ae-section-label">DEVICE</div>
        <div class="ae-device-row">
          <div class="ae-device-icon-wrap">
            <ha-icon icon="mdi:cellphone-sound"></ha-icon>
          </div>
          <div class="ae-device-info">
            <div class="ae-device-name">${this._config.device_name}</div>
            <div class="ae-device-sub">by AllEars</div>
          </div>
          <ha-icon icon="mdi:chevron-right" class="ae-chevron"></ha-icon>
        </div>
        <div class="ae-attr-row"><span class="ae-label">FIRMWARE</span><span class="ae-row-right"><b>${this._config.firmware}</b> <span class="ae-badge-sm">Up to date</span></span></div>
        <div class="ae-attr-row"><span class="ae-label">INTEGRATION</span><span>AllEars HACS</span></div>
        <div class="ae-attr-row"><span class="ae-label">LOCATION</span><span>${this._config.location}</span></div>
        <div class="ae-attr-row"><span class="ae-label">WEBHOOK</span><span class="ae-mono ae-clip" id="dev-webhook-id">—</span></div>
      </div>

      <!-- Activity log card -->
      <div class="ae-card">
        <div class="ae-section-label">ACTIVITY</div>
        <div id="act-list" class="ae-act-list">
          <div class="ae-empty-state">
            <ha-icon icon="mdi:ear-hearing" class="ae-empty-icon"></ha-icon>
            <div class="ae-empty-copy">No activity recorded yet</div>
          </div>
        </div>
        <button class="ae-btn ae-btn-outline ae-btn-full" id="btn-simulate">
          <ha-icon icon="mdi:microphone-outline"></ha-icon>
          Simulate sound event
        </button>
        <button class="ae-btn ae-btn-ghost ae-btn-full" id="btn-clear-history" style="margin-top:8px">
          <ha-icon icon="mdi:trash-can-outline"></ha-icon>
          Clear history
        </button>
      </div>
    `;
  }

  _panelSettings() {
    return `
      <!-- Connection Settings -->
      <div class="ae-card">
        <div class="ae-section-label">CONNECTION</div>
        <div class="ae-attr-row ae-attr-row--pad">
          <div>
            <div class="ae-setting-label">Webhook URL</div>
            <div class="ae-setting-sub">Used by the AllEars Android app</div>
          </div>
        </div>
        <div class="ae-webhook-url-row">
          <input class="ae-input" id="wh-url-input" readonly placeholder="Loading…" />
          <button class="ae-icon-btn" id="btn-copy-wh" title="Copy URL"><ha-icon icon="mdi:content-copy"></ha-icon></button>
        </div>
        <div class="ae-attr-row ae-attr-row--pad" style="margin-top:16px">
          <div>
            <div class="ae-setting-label">Device Name</div>
            <div class="ae-setting-sub">Label shown in Home Assistant</div>
          </div>
        </div>
        <div class="ae-webhook-url-row">
          <input class="ae-input" id="device-name-input" value="${this._config.device_name}" />
          <button class="ae-icon-btn" id="btn-save-name" title="Save"><ha-icon icon="mdi:check"></ha-icon></button>
        </div>
      </div>

      <!-- Notifications Settings -->
      <div class="ae-card">
        <div class="ae-section-label">NOTIFICATIONS</div>
        <div class="ae-setting-row" id="set-notif">
          <div>
            <div class="ae-setting-label">Enable notifications</div>
            <div class="ae-setting-sub">Receive alerts when a flow triggers</div>
          </div>
          <div class="ae-toggle ${this._settings.notifications ? 'on' : ''}" data-key="notifications" role="switch" tabindex="0"></div>
        </div>
        <div class="ae-setting-row" id="set-alerts">
          <div>
            <div class="ae-setting-label">Sound active alerts</div>
            <div class="ae-setting-sub">Alert while sound detection is active</div>
          </div>
          <div class="ae-toggle ${this._settings.soundAlerts ? 'on' : ''}" data-key="soundAlerts" role="switch" tabindex="0"></div>
        </div>
        <div class="ae-setting-row" id="set-log">
          <div>
            <div class="ae-setting-label">Log all events</div>
            <div class="ae-setting-sub">Keep an event history in the Activity tab</div>
          </div>
          <div class="ae-toggle ${this._settings.logEvents ? 'on' : ''}" data-key="logEvents" role="switch" tabindex="0"></div>
        </div>
      </div>

      <!-- Diagnostics -->
      <div class="ae-card">
        <div class="ae-section-label">DIAGNOSTICS</div>
        <button class="ae-btn ae-btn-outline ae-btn-full" id="btn-test-wh">
          <ha-icon icon="mdi:webhook"></ha-icon>
          Send test webhook event
        </button>
        <button class="ae-btn ae-btn-danger ae-btn-full" id="btn-factory-reset" style="margin-top:8px">
          <ha-icon icon="mdi:delete-forever"></ha-icon>
          Clear all data
        </button>
      </div>
    `;
  }

  // ─── State Sync (runs on every hass update) ──────────────────────────────

  _getFilteredLatestSound() {
    if (this._selectedFlow === 'All Flows') {
      return this._sensorVal(this._soundSensorId);
    }
    const matched = this._activityLog.find(e => e.flow === this._selectedFlow);
    return matched ? matched.sound : 'Waiting...';
  }

  _getFilteredLatestFlow() {
    if (this._selectedFlow === 'All Flows') {
      return this._sensorVal(this._flowSensorId);
    }
    const matched = this._activityLog.find(e => e.flow === this._selectedFlow);
    return matched ? matched.flow : 'Waiting...';
  }

  _syncState(prev) {
    const root = this._root;
    const state = this._activeState;

    // ── Header pill ──
    const pill = root.querySelector('#hdr-pill');
    const dot = root.querySelector('#hdr-dot');
    const pillLabel = root.querySelector('#hdr-pill-label');
    const hdrIcon = root.querySelector('#hdr-icon');
    const hdrHaIcon = root.querySelector('#hdr-ha-icon');

    if (pill) {
      pill.className = 'ae-status-pill';
      if (state === 'active') { pill.classList.add('ae-pill-active'); pillLabel.textContent = 'Active'; }
      else if (state === 'unavailable') { pill.classList.add('ae-pill-unavail'); pillLabel.textContent = 'Unavailable'; }
      else if (state === 'empty') { pill.classList.add('ae-pill-unavail'); pillLabel.textContent = 'Not found'; }
      else { pillLabel.textContent = 'Listening'; }

      hdrIcon.className = 'ae-header-icon' + (state === 'active' ? ' active' : '');
      if (hdrHaIcon) hdrHaIcon.setAttribute('icon', state === 'unavailable' ? 'mdi:ear-hearing-off' : 'mdi:ear-hearing');
    }

    // ── Monitor card ──
    const monSound = root.querySelector('#mon-sound');
    if (monSound) {
      const sv = this._sensorVal(this._soundSensorId);
      monSound.textContent = state === 'active' ? sv : state === 'unavailable' ? 'Unavailable' : 'Listening...';
    }

    // ── Overview sensor tiles ──
    this._setText('#ov-sound-val', this._getFilteredLatestSound());
    this._setText('#ov-flow-val', this._getFilteredLatestFlow());

    const activeTile = root.querySelector('#ov-active-val-tile');
    const activeVal = root.querySelector('#ov-active-val');
    if (activeVal) {
      const isOn = state === 'active';
      activeVal.textContent = isOn ? 'Active' : 'Clear';
      if (activeTile) {
        activeTile.className = 'ae-sensor-tile ' + (isOn ? 'ae-tile-active' : 'ae-tile-clear');
      }
    }

    // ── Sensors panel ──
    this._setText('#sd-sound-val', this._sensorVal(this._soundSensorId));
    this._setText('#sd-flow-val', this._sensorVal(this._flowSensorId));
    this._setText('#sd-active-val', state === 'active' ? 'Active' : state === 'unavailable' ? 'Unavailable' : 'Clear');

    const sdActiveWrap = root.querySelector('#sd-active-wrap');
    if (sdActiveWrap) {
      sdActiveWrap.className = 'ae-sensor-detail-icon-wrap ' + (state === 'active' ? 'amber' : 'green');
    }

    // ── Activity: webhook entity id ──
    this._populateWebhookId();

    // ── Flow filter dropdown sync ──
    this._syncFlowDropdown();

    // ── Append to activity log if state changed to active ──
    if (prev && this._activeState === 'active') {
      const prevBin = prev.states[this._binarySensorId];
      const curBin = this._hass.states[this._binarySensorId];
      if (prevBin && curBin && prevBin.state !== 'on' && curBin.state === 'on') {
        const flowVal = this._sensorVal(this._flowSensorId);
        const soundVal = this._sensorVal(this._soundSensorId);
        this._addActivityEntry(soundVal, flowVal);
      }
    }
  }

  _syncFlowDropdown() {
    const selectEl = this._root?.querySelector('#flow-select');
    if (!selectEl) return;

    const entity = this._hass?.states[this._selectEntityId];
    const options = entity?.attributes?.options || ['All Flows'];
    const current = entity?.state || 'All Flows';

    // Rebuild options only if they have changed (avoids flickering)
    const currentOpts = [...selectEl.options].map(o => o.value);
    const same = options.length === currentOpts.length &&
                 options.every((o, i) => o === currentOpts[i]);
    if (!same) {
      selectEl.innerHTML = options
        .map(o => `<option value="${o}"${o === current ? ' selected' : ''}>${o}</option>`)
        .join('');
    } else if (selectEl.value !== current) {
      selectEl.value = current;
    }

    this._selectedFlow = current;

    const hint = this._root?.querySelector('#flow-hint');
    if (hint) {
      hint.textContent = current === 'All Flows'
        ? 'Showing all events'
        : `Filtering: ${current}`;
    }
  }

  _populateWebhookId() {
    const root = this._root;
    // Look through all hass entities to find a config entry for allears
    const allEarsConfig = Object.values(this._hass?.states || {}).find(e =>
      e.entity_id.startsWith('binary_sensor.allears') || e.entity_id.startsWith('sensor.allears')
    );
    const ha_url = this._hass?.config?.external_url || this._hass?.config?.internal_url || window.location.origin;
    const webhookId = allEarsConfig?.attributes?.webhook_id || '<webhook-id>';
    const fullUrl = `${ha_url}/api/webhook/${webhookId}`;

    const whInput = root.querySelector('#wh-url-input');
    if (whInput) whInput.value = fullUrl;

    const webhookEl = root.querySelector('#dev-webhook-id');
    if (webhookEl) webhookEl.textContent = webhookId;
  }

  _addActivityEntry(sound, flow) {
    if (!this._settings.logEvents) return;
    const now = new Date();
    this._activityLog.unshift({ sound, flow, time: now });
    if (this._activityLog.length > 50) this._activityLog.pop();
    this._renderActivityList();
  }

  _renderActivityList() {
    const list = this._root.querySelector('#act-list');
    if (!list) return;

    const displayLog = this._selectedFlow === 'All Flows' 
      ? this._activityLog 
      : this._activityLog.filter(e => e.flow === this._selectedFlow);

    if (displayLog.length === 0) {
      list.innerHTML = `
        <div class="ae-empty-state">
          <ha-icon icon="mdi:ear-hearing" class="ae-empty-icon"></ha-icon>
          <div class="ae-empty-copy">No activity recorded yet</div>
        </div>`;
      return;
    }
    list.innerHTML = displayLog.map(e => `
      <div class="ae-act-row">
        <div class="ae-act-icon-wrap"><ha-icon icon="mdi:microphone"></ha-icon></div>
        <div class="ae-act-body">
          <div class="ae-act-sound">${e.sound}</div>
          <div class="ae-act-meta">${e.flow} · ${this._fmtTime(e.time)}</div>
        </div>
      </div>
    `).join('');
  }

  // ─── Event listeners ─────────────────────────────────────────────────────

  _attachListeners() {
    const root = this._root;

    // Tabs
    root.addEventListener('click', e => {
      const tab = e.target.closest('.ae-tab');
      if (tab) { this._switchTab(tab.dataset.tab); return; }

      // Simulate / Test webhook
      if (e.target.closest('#btn-simulate') || e.target.closest('#btn-test-wh')) {
        this._callService('test_webhook');
        this._addActivityEntry('Test Sound', 'Test Flow');
        this._showToast('Test event fired ✓');
        return;
      }

      // Clear history
      if (e.target.closest('#btn-clear-history') || e.target.closest('#btn-factory-reset')) {
        this._callService('clear_history');
        this._activityLog = [];
        this._renderActivityList();
        this._showToast('History cleared');
        return;
      }

      // + Add action shortcuts — deep-link into HA with allears pre-filled
      const addBtn = e.target.closest('.ae-add-btn');
      if (addBtn && this._hass) {
        const action = addBtn.dataset.action;
        if (action === 'automation') {
          // Pre-fill the automation editor with the allears_sound_detected event trigger
          window.history.pushState(
            null, '',
            '/config/automation/new?trigger_type=event&event_type=allears_sound_detected'
          );
          window.dispatchEvent(new PopStateEvent('popstate'));
        } else {
          window.history.pushState(null, '', `/${action}s/new`);
          window.dispatchEvent(new PopStateEvent('popstate'));
        }
        return;
      }

      // Flow filter dropdown change (native select fires change, not click)
      // — handled in change listener below

      // Copy webhook URL
      if (e.target.closest('#btn-copy-wh')) {
        const val = root.querySelector('#wh-url-input')?.value;
        if (val) { navigator.clipboard.writeText(val); this._showToast('Copied to clipboard ✓'); }
        return;
      }

      // Save device name
      if (e.target.closest('#btn-save-name')) {
        const val = root.querySelector('#device-name-input')?.value?.trim();
        if (val) { this._config.device_name = val; this._showToast('Saved'); }
        return;
      }

      // Toggle switches
      const toggle = e.target.closest('.ae-toggle');
      if (toggle) {
        const key = toggle.dataset.key;
        this._settings[key] = !this._settings[key];
        toggle.classList.toggle('on', this._settings[key]);
        return;
      }
    });

    // Flow filter select — change event
    root.addEventListener('change', e => {
      const sel = e.target.closest('#flow-select');
      if (sel && this._hass) {
        const chosen = sel.value;
        this._selectedFlow = chosen;
        // Write back to the HA select entity
        this._hass.callService('select', 'select_option', {
          entity_id: this._selectEntityId,
          option: chosen,
        });
        const hint = root.querySelector('#flow-hint');
        if (hint) hint.textContent = chosen === 'All Flows' ? 'Showing all events' : `Filtering: ${chosen}`;
        this._setText('#ov-sound-val', this._getFilteredLatestSound());
        this._setText('#ov-flow-val', this._getFilteredLatestFlow());
        this._renderActivityList();
      }
    });

    // Keyboard accessibility for toggles
    root.addEventListener('keydown', e => {
      if ((e.key === ' ' || e.key === 'Enter') && e.target.classList.contains('ae-toggle')) {
        e.preventDefault();
        e.target.click();
      }
    });
  }

  _switchTab(tab) {
    this._activeTab = tab;
    const root = this._root;
    root.querySelectorAll('.ae-tab').forEach(t => {
      const active = t.dataset.tab === tab;
      t.classList.toggle('active', active);
      t.setAttribute('aria-selected', active);
    });
    root.querySelectorAll('.ae-panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${tab}`);
    });
    // Refresh webhook display when switching to activity/settings
    if (tab === 'activity' || tab === 'settings') {
      this._populateWebhookId();
    }
    if (tab === 'activity') {
      this._renderActivityList();
    }
  }

  _showToast(msg) {
    const existing = this.shadowRoot.querySelector('.ae-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'ae-toast';
    toast.textContent = msg;
    this.shadowRoot.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('ae-toast-in'));
    setTimeout(() => {
      toast.classList.remove('ae-toast-in');
      setTimeout(() => toast.remove(), 300);
    }, 2200);
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  _setText(selector, value) {
    const el = this._root?.querySelector(selector);
    if (el) el.textContent = value;
  }

  _fmtTime(ts) {
    try {
      const d = ts instanceof Date ? ts : new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return '—'; }
  }

  // ─── Styles ───────────────────────────────────────────────────────────────

  _styles() {
    return `
      :host {
        display: block;
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        color: var(--primary-text-color);
      }

      *, *::before, *::after { box-sizing: border-box; }

      /* ── Root wrapper ── */
      .ae-root {
        background: var(--primary-background-color, #111318);
        border-radius: var(--ha-card-border-radius, 16px);
        overflow: hidden;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255,255,255,0.08)));
        box-shadow: var(--ha-card-box-shadow, none);
      }

      /* ── Cards inside ── */
      .ae-card {
        background: var(--card-background-color, #1c1e26);
        border-radius: 16px;
        border: 1px solid var(--ha-card-border-color, var(--divider-color, rgba(255,255,255,0.06)));
        box-shadow: 0 2px 12px rgba(0,0,0,0.02);
        padding: 24px;
        margin: 0 24px 24px;
      }

      /* ── Header ── */
      .ae-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 24px 24px 16px;
        gap: 16px;
      }
      .ae-header-left { display: flex; align-items: center; gap: 16px; }
      .ae-title { font-size: 22px; font-weight: 500; color: var(--primary-text-color); letter-spacing: -0.2px; }
      .ae-subtitle { font-size: 14px; color: var(--secondary-text-color); margin-top: 4px; }

      .ae-header-icon {
        width: 44px; height: 44px; border-radius: 50%;
        background: var(--secondary-background-color, rgba(120,120,120,0.15));
        display: flex; align-items: center; justify-content: center;
        color: var(--primary-text-color);
        transition: background 0.3s, color 0.3s;
        flex-shrink: 0;
      }
      .ae-header-icon.active { background: var(--warning-color); color: #fff; }
      .ae-header-icon.active .ae-wave { display: flex; }
      .ae-header-icon.active ha-icon { display: none; }

      .ae-wave {
        display: none; align-items: center; gap: 3px; height: 22px;
      }
      .ae-wave span {
        display: block; width: 3px; border-radius: 2px;
        background: currentColor;
        animation: ae-pulse 1s ease-in-out infinite alternate;
      }
      .ae-wave span:nth-child(1) { height: 40%; animation-delay: 0s; }
      .ae-wave span:nth-child(2) { height: 100%; animation-delay: 0.2s; }
      .ae-wave span:nth-child(3) { height: 60%; animation-delay: 0.1s; }
      .ae-wave span:nth-child(4) { height: 80%; animation-delay: 0.3s; }
      @keyframes ae-pulse {
        from { transform: scaleY(0.3); }
        to   { transform: scaleY(1); }
      }

      /* ── Status pill ── */
      .ae-status-pill {
        display: flex; align-items: center; gap: 8px;
        padding: 6px 14px; border-radius: 999px;
        font-size: 13px; font-weight: 500;
        background: rgba(3,169,244,0.15);
        color: var(--info-color, #03a9f4);
        border: 1px solid rgba(3,169,244,0.25);
        transition: background 0.3s, color 0.3s, border-color 0.3s;
        white-space: nowrap;
      }
      .ae-pill-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: currentColor;
        animation: ae-blink 2s ease-in-out infinite;
      }
      .ae-status-pill.ae-pill-active {
        background: rgba(255,152,0,0.15); color: var(--warning-color, #ff9800);
        border-color: rgba(255,152,0,0.3);
      }
      .ae-status-pill.ae-pill-unavail {
        background: rgba(128,128,128,0.1); color: var(--disabled-text-color, #888);
        border-color: rgba(128,128,128,0.15);
      }
      @keyframes ae-blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }

      /* ── Tab bar ── */
      .ae-tabs {
        display: flex; gap: 8px;
        padding: 0 24px 16px;
        border-bottom: 1px solid var(--divider-color, rgba(255,255,255,0.06));
        overflow-x: auto;
        scrollbar-width: none;
      }
      .ae-tabs::-webkit-scrollbar { display: none; }

      .ae-tab {
        appearance: none; border: none; background: none; cursor: pointer;
        font: 500 14px/1 'Roboto', sans-serif;
        letter-spacing: 0.3px;
        color: var(--secondary-text-color);
        padding: 10px 16px;
        border-radius: 8px;
        min-height: 44px;
        transition: background 0.2s, color 0.2s;
        white-space: nowrap;
      }
      .ae-tab:hover { background: var(--secondary-background-color, rgba(120,120,120,0.1)); color: var(--primary-text-color); }
      .ae-tab.active { background: var(--secondary-background-color, rgba(120,120,120,0.15)); color: var(--primary-text-color); }

      /* ── Panels ── */
      .ae-panel { display: none; padding-top: 20px; }
      .ae-panel.active { display: block; }

      /* ── Section label ── */
      .ae-section-label {
        font-size: 11px; font-weight: 500;
        letter-spacing: 0.8px; text-transform: uppercase;
        color: var(--secondary-text-color);
        margin-bottom: 12px;
      }

      /* ── Monitor card ── */
      .ae-monitor-card { position: relative; min-height: 160px; }
      .ae-monitor-top {
        display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;
        margin-bottom: 40px;
      }
      .ae-monitor-title { font-size: 22px; font-weight: 500; }
      .ae-monitor-meta  { font-size: 14px; color: var(--secondary-text-color); margin-top: 4px; }
      .ae-monitor-bottom {
        display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
      }
      .ae-label {
        font-size: 12px; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.8px; color: var(--secondary-text-color);
      }
      .ae-monitor-sound { font-size: 26px; font-weight: 400; color: var(--primary-text-color); }

      /* ── Badge ── */
      .ae-badge {
        font-size: 11px; font-weight: 500;
        background: var(--secondary-background-color, rgba(120,120,120,0.15));
        color: var(--secondary-text-color);
        padding: 4px 10px; border-radius: 999px;
        border: 1px solid var(--divider-color);
        white-space: nowrap;
      }
      .ae-badge-sm {
        font-size: 11px; font-weight: 500;
        background: rgba(76,175,80,0.15);
        color: var(--success-color, #4caf50);
        padding: 2px 8px; border-radius: 999px;
        border: 1px solid rgba(76,175,80,0.25);
      }

      /* ── Sensor grid (overview) ── */
      .ae-sensor-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
      }
      @media (max-width: 400px) {
        .ae-sensor-grid { grid-template-columns: 1fr; }
      }
      .ae-sensor-tile {
        background: var(--secondary-background-color, rgba(120,120,120,0.08));
        border-radius: 10px; padding: 12px;
        border-left: 4px solid var(--divider-color);
        display: flex; flex-direction: column; gap: 6px;
        transition: border-left-color 0.3s;
        min-height: 44px;
      }
      .ae-sensor-tile.ae-tile-clear  { border-left-color: var(--success-color, #4caf50); }
      .ae-sensor-tile.ae-tile-active { border-left-color: var(--warning-color, #ff9800); }

      .ae-sensor-icon-wrap {
        width: 32px; height: 32px; border-radius: 8px;
        background: rgba(3,169,244,0.12);
        display: flex; align-items: center; justify-content: center;
        color: var(--info-color, #03a9f4);
        --mdc-icon-size: 18px;
      }
      .ae-sensor-label { font-size: 11px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.6px; color: var(--secondary-text-color); }
      .ae-sensor-value { font-size: 16px; font-weight: 400; color: var(--primary-text-color); }

      /* ── Quick Actions grid ── */
      .ae-action-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
      }
      @media (max-width: 400px) {
        .ae-action-grid { grid-template-columns: 1fr; }
      }
      .ae-action-tile {
        background: var(--secondary-background-color, rgba(120,120,120,0.08));
        border-radius: 10px; padding: 12px;
        display: flex; flex-direction: column; align-items: center; gap: 6px;
        text-align: center; min-height: 44px;
        border: 1px solid var(--divider-color);
      }
      .ae-action-icon { color: var(--warning-color, #ff9800); --mdc-icon-size: 24px; }
      .ae-action-name { font-size: 13px; font-weight: 500; }
      .ae-action-sub  { font-size: 11px; color: var(--secondary-text-color); }
      .ae-add-btn {
        appearance: none; background: none; border: none;
        color: var(--primary-color, #03a9f4);
        font-size: 12px; font-weight: 500; cursor: pointer;
        padding: 4px 8px; border-radius: 6px;
        min-height: 44px; width: 100%;
        transition: background 0.2s;
      }
      .ae-add-btn:hover { background: rgba(3,169,244,0.1); }

      /* ── Flow filter dropdown ── */
      .ae-flow-filter-wrap {
        display: flex; align-items: center; gap: 10px;
        background: var(--secondary-background-color, rgba(120,120,120,0.08));
        border: 1px solid var(--divider-color, rgba(255,255,255,0.08));
        border-radius: 10px; padding: 10px 14px;
      }
      .ae-flow-icon { color: var(--info-color, #03a9f4); --mdc-icon-size: 20px; flex-shrink: 0; }
      .ae-flow-select {
        flex: 1; appearance: none;
        background: transparent;
        border: none; outline: none;
        color: var(--primary-text-color);
        font: 500 14px/1 'Roboto', sans-serif;
        cursor: pointer;
      }
      .ae-flow-select option { background: var(--card-background-color, #1c1e26); color: var(--primary-text-color); }
      .ae-flow-hint { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; }

      /* ── Sensor detail cards ── */
      .ae-sensor-detail-card { }
      .ae-sensor-detail-header {
        display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
      }
      .ae-sensor-detail-icon-wrap {
        width: 44px; height: 44px; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; --mdc-icon-size: 22px;
        transition: background 0.3s;
      }
      .ae-sensor-detail-icon-wrap.blue  { background: rgba(3,169,244,0.15); color: var(--info-color, #03a9f4); }
      .ae-sensor-detail-icon-wrap.amber { background: rgba(255,152,0,0.15); color: var(--warning-color, #ff9800); }
      .ae-sensor-detail-icon-wrap.green { background: rgba(76,175,80,0.15); color: var(--success-color, #4caf50); }

      .ae-sensor-detail-value { font-size: 22px; font-weight: 400; color: var(--primary-text-color); margin-top: 4px; }
      .ae-sensor-attrs { display: flex; flex-direction: column; gap: 8px; }
      .ae-attr-row {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 13px;
        padding: 4px 0;
        border-top: 1px solid var(--divider-color, rgba(255,255,255,0.05));
        gap: 8px;
      }
      .ae-attr-row:first-child { border-top: none; }
      .ae-attr-row--pad { padding: 8px 0; border-top: none; }
      .ae-row-right { display: flex; align-items: center; gap: 8px; }

      /* ── Device row ── */
      .ae-device-row {
        display: flex; align-items: center; gap: 12px;
        background: var(--secondary-background-color, rgba(120,120,120,0.08));
        padding: 12px; border-radius: 10px; margin-bottom: 12px;
        border: 1px solid var(--divider-color);
        min-height: 64px;
      }
      .ae-device-icon-wrap {
        width: 44px; height: 44px; border-radius: 12px;
        background: rgba(3,169,244,0.15); color: var(--info-color, #03a9f4);
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; --mdc-icon-size: 24px;
      }
      .ae-device-info { flex: 1; }
      .ae-device-name { font-size: 15px; font-weight: 500; }
      .ae-device-sub  { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }
      .ae-chevron { color: var(--secondary-text-color); --mdc-icon-size: 18px; }

      /* ── Activity list ── */
      .ae-act-list { margin-bottom: 12px; min-height: 80px; }
      .ae-act-row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 0;
        border-top: 1px solid var(--divider-color, rgba(255,255,255,0.05));
      }
      .ae-act-row:first-child { border-top: none; }
      .ae-act-icon-wrap {
        width: 36px; height: 36px; border-radius: 50%;
        background: rgba(3,169,244,0.12); color: var(--info-color, #03a9f4);
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; --mdc-icon-size: 18px;
      }
      .ae-act-sound { font-size: 14px; font-weight: 500; }
      .ae-act-meta  { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }

      /* ── Empty state ── */
      .ae-empty-state {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; padding: 24px 16px; gap: 12px; text-align: center;
      }
      .ae-empty-icon { color: var(--disabled-text-color, #555); --mdc-icon-size: 40px; }
      .ae-empty-copy { font-size: 14px; color: var(--secondary-text-color); }

      /* ── Settings ── */
      .ae-setting-row {
        display: flex; align-items: center; justify-content: space-between; gap: 12px;
        padding: 12px 0; min-height: 44px;
        border-top: 1px solid var(--divider-color, rgba(255,255,255,0.06));
      }
      .ae-setting-row:first-of-type { border-top: none; }
      .ae-setting-label { font-size: 14px; font-weight: 400; }
      .ae-setting-sub   { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; }

      /* Toggle switch */
      .ae-toggle {
        width: 44px; height: 26px; border-radius: 13px;
        background: var(--divider-color, rgba(120,120,120,0.3));
        position: relative; cursor: pointer; flex-shrink: 0;
        transition: background 0.3s;
      }
      .ae-toggle::after {
        content: ''; position: absolute; top: 3px; left: 3px;
        width: 20px; height: 20px; border-radius: 50%;
        background: #fff; transition: transform 0.25s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4);
      }
      .ae-toggle.on { background: var(--primary-color, #03a9f4); }
      .ae-toggle.on::after { transform: translateX(18px); }

      /* ── Webhook URL row ── */
      .ae-webhook-url-row {
        display: flex; gap: 8px; align-items: center;
        margin-bottom: 8px;
      }
      .ae-input {
        flex: 1; appearance: none; border: 1px solid var(--divider-color);
        border-radius: 8px; padding: 10px 12px;
        background: var(--secondary-background-color, rgba(120,120,120,0.08));
        color: var(--primary-text-color); font-size: 13px;
        font-family: inherit; outline: none; min-height: 44px;
        transition: border-color 0.2s;
      }
      .ae-input:focus { border-color: var(--primary-color, #03a9f4); }
      .ae-mono { font-family: 'Roboto Mono', monospace; font-size: 12px; }
      .ae-clip { word-break: break-all; }
      .ae-icon-btn {
        width: 44px; height: 44px; flex-shrink: 0;
        appearance: none; background: var(--secondary-background-color);
        border: 1px solid var(--divider-color); border-radius: 8px;
        color: var(--primary-text-color); cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: background 0.2s;
      }
      .ae-icon-btn:hover { background: rgba(3,169,244,0.1); color: var(--primary-color, #03a9f4); }

      /* ── Buttons ── */
      .ae-btn {
        appearance: none; font: 500 14px/1 'Roboto', sans-serif;
        border-radius: 10px; padding: 12px 16px;
        cursor: pointer; display: flex; align-items: center;
        justify-content: center; gap: 8px;
        min-height: 44px; transition: background 0.2s, opacity 0.2s;
      }
      .ae-btn-full { width: 100%; }
      .ae-btn-outline {
        background: transparent;
        border: 1px solid var(--divider-color);
        color: var(--primary-text-color);
      }
      .ae-btn-outline:hover { background: var(--secondary-background-color); }
      .ae-btn-ghost {
        background: transparent; border: none;
        color: var(--secondary-text-color);
      }
      .ae-btn-ghost:hover { color: var(--primary-text-color); background: var(--secondary-background-color); }
      .ae-btn-danger {
        background: rgba(244,67,54,0.1);
        border: 1px solid rgba(244,67,54,0.25);
        color: var(--error-color, #f44336);
      }
      .ae-btn-danger:hover { background: rgba(244,67,54,0.2); }

      /* ── Toast ── */
      .ae-toast {
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px);
        background: var(--primary-text-color); color: var(--primary-background-color);
        font-size: 13px; font-weight: 500;
        padding: 10px 20px; border-radius: 999px;
        pointer-events: none; opacity: 0;
        transition: opacity 0.25s, transform 0.25s;
        z-index: 9999;
        white-space: nowrap;
      }
      .ae-toast.ae-toast-in { opacity: 1; transform: translateX(-50%) translateY(0); }
    `;
  }
}

customElements.define('all-ears-card', AllEarsCard);
window.customCards = window.customCards || [];
// Avoid duplicate registration on hot-reload
if (!window.customCards.find(c => c.type === 'all-ears-card')) {
  window.customCards.push({
    type: 'all-ears-card',
    name: 'AllEars Sound Tracker',
    preview: true,
    description: 'Full dashboard card for the AllEars Home Assistant integration.',
  });
}
