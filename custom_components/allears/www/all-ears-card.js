/**
 * AllEars dashboard card.
 *
 * Finds the AllEars entities by device (no hard-coded entity ids), shows the
 * live listening state, the last sound with its flow and confidence, the
 * phone's connection status, the registered flows and the recent history from
 * the recorder. Vanilla web component, HA theme variables only.
 */

const AE_DOMAIN = 'allears';
const AE_VERSION = '1.1.0';
const AE_ALL_FLOWS = 'All Flows';

const aeEsc = (v) =>
  String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function aeAgo(ms, now = Date.now()) {
  if (!ms) return '';
  const s = Math.max(0, Math.round((now - ms) / 1000));
  if (s < 45) return 'just now';
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  return `${d} d ago`;
}

/** All AllEars devices, each with its entities, from the frontend registries. */
function aeDevices(hass) {
  const devices = {};
  for (const ent of Object.values(hass?.entities || {})) {
    if (ent.platform !== AE_DOMAIN || !ent.device_id) continue;
    const dev = (devices[ent.device_id] ||= { id: ent.device_id, entities: {} });
    const [domain] = ent.entity_id.split('.');
    let role = ent.translation_key;
    if (!role) {
      // Fallback for registries without translation keys.
      if (domain === 'binary_sensor') role = 'sound_active';
      else if (domain === 'select') role = 'active_flow_filter';
      else if (/seen/.test(ent.entity_id)) role = 'last_seen';
      else if (/flow/.test(ent.entity_id)) role = 'last_flow';
      else role = 'last_sound';
    }
    dev.entities[role] = ent.entity_id;
  }
  for (const dev of Object.values(devices)) {
    const reg = hass.devices?.[dev.id];
    dev.name = reg?.name_by_user || reg?.name || 'AllEars';
  }
  return Object.values(devices);
}

class AllEarsCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('all-ears-card-editor');
  }

  static getStubConfig(hass) {
    const dev = aeDevices(hass)[0];
    return dev ? { device_id: dev.id } : {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._history = [];
    this._historyFor = null;
    this._filter = AE_ALL_FLOWS;
    this._lastKey = '';
  }

  setConfig(config) {
    this._config = { show_history: true, history_hours: 24, ...(config || {}) };
    this._lastKey = '';
    this._historyFor = null;
    if (this._hass) this._update(true);
  }

  set hass(hass) {
    this._hass = hass;
    this._update(false);
  }

  connectedCallback() {
    // Keep "x min ago" labels fresh.
    this._tick = setInterval(() => this._update(true), 30000);
  }

  disconnectedCallback() {
    clearInterval(this._tick);
  }

  getCardSize() {
    return this._config?.show_history ? 7 : 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 'auto' };
  }

  // ── Data ───────────────────────────────────────────────────────────────

  _device() {
    const devices = aeDevices(this._hass);
    if (this._config.device_id) return devices.find((d) => d.id === this._config.device_id) || null;
    return devices[0] || null;
  }

  _state(id) {
    return id ? this._hass.states[id] : undefined;
  }

  _usable(st) {
    return st && st.state !== 'unknown' && st.state !== 'unavailable';
  }

  async _loadHistory(dev) {
    const id = dev.entities.last_sound;
    if (!id || !this._config.show_history) return;
    const key = `${id}|${this._config.history_hours}`;
    if (this._historyFor === key) return;
    this._historyFor = key;
    const end = new Date();
    const start = new Date(end.getTime() - Number(this._config.history_hours || 24) * 3600 * 1000);
    try {
      const res = await this._hass.callWS({
        type: 'history/history_during_period',
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: [id],
        minimal_response: false,
        no_attributes: false,
        significant_changes_only: false,
      });
      const rows = [];
      let attrs = {};
      for (const r of res?.[id] || []) {
        if (r.a) attrs = r.a;
        if (!r.s || r.s === 'unknown' || r.s === 'unavailable') continue;
        rows.push(this._row(r.s, attrs, (r.lu || r.lc || 0) * 1000));
      }
      this._history = this._dedupe(rows).slice(0, 50);
    } catch (err) {
      // Non-admin users or recorder disabled: keep the live list only.
      this._history = this._history || [];
    }
    this._lastKey = '';
    this._update(true);
  }

  _row(sound, attrs, fallbackMs) {
    const t = Date.parse(attrs.timestamp || attrs.last_updated || '') || fallbackMs;
    return {
      sound,
      flow: attrs.flow_name || '',
      confidence: typeof attrs.confidence === 'number' ? attrs.confidence : null,
      t,
    };
  }

  _dedupe(rows) {
    const seen = new Set();
    return rows
      .sort((a, b) => b.t - a.t)
      .filter((r) => {
        const k = `${r.t}|${r.sound}|${r.flow}`;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
  }

  _trackLive(soundSt) {
    if (!this._usable(soundSt)) return;
    const row = this._row(soundSt.state, soundSt.attributes || {}, Date.parse(soundSt.last_updated));
    const head = this._history[0];
    if (!head || head.t !== row.t || head.sound !== row.sound) {
      this._history = this._dedupe([row, ...this._history]).slice(0, 50);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────

  _update(force) {
    if (!this._hass || !this._config) return;
    const dev = this._device();
    if (!dev) {
      this._renderMissing();
      return;
    }
    const e = dev.entities;
    const sound = this._state(e.last_sound);
    const active = this._state(e.sound_active);
    const seen = this._state(e.last_seen);
    const select = this._state(e.active_flow_filter);
    const key = [dev.name, sound?.last_updated, active?.state, seen?.state, select?.state,
      (select?.attributes?.options || []).join('\u0001'), this._history.length].join('|');
    if (!force && key === this._lastKey) return;
    this._lastKey = key;

    this._trackLive(sound);
    this._loadHistory(dev);
    this._render(dev, { sound, active, seen, select });
  }

  _renderMissing() {
    if (this._lastKey === 'missing') return;
    this._lastKey = 'missing';
    const admin = this._hass.user?.is_admin;
    this.shadowRoot.innerHTML = `<style>${AE_STYLES}</style>
      <ha-card><div class="wrap">
        ${this._header('AllEars', 'off', 'Not set up')}
        <div class="setup">
          <p><b>No AllEars phone found.</b></p>
          <p class="muted">Add the AllEars integration, then paste its webhook URL into a flow's <b>Trigger Webhook</b> action in the AllEars app.</p>
          ${admin ? '<button class="btn primary" data-nav="/config/integrations/integration/allears">Open AllEars integration</button>' : ''}
        </div>
      </div></ha-card>`;
    this._bind();
  }

  _header(title, mode, status) {
    return `<div class="head">
      <div class="ear ${mode}"><span class="ring"></span><span class="ring r2"></span><ha-icon icon="${mode === 'off' ? 'mdi:ear-hearing-off' : 'mdi:ear-hearing'}"></ha-icon></div>
      <div class="ttl"><div class="name">${aeEsc(title)}</div><div class="status ${mode}">${aeEsc(status)}</div></div>
    </div>`;
  }

  _render(dev, { sound, active, seen, select }) {
    const admin = this._hass.user?.is_admin;
    const now = Date.now();
    const isActive = active?.state === 'on';
    const unavailable = active?.state === 'unavailable';
    const seenMs = this._usable(seen) ? Date.parse(seen.state) : null;
    const hasSound = this._usable(sound);
    const flows = (select?.attributes?.options || []).filter((o) => o !== AE_ALL_FLOWS);
    const connected = !!seenMs || hasSound || flows.length > 0;

    let mode = 'idle';
    let status = seenMs ? `Connected · phone seen ${aeAgo(seenMs, now)}` : 'Waiting for the phone';
    if (unavailable) { mode = 'off'; status = 'Unavailable'; }
    else if (isActive) { mode = 'active'; status = 'Sound detected now'; }
    else if (!connected) { mode = 'off'; }

    const title = this._config.title || dev.name;
    const a = sound?.attributes || {};
    const heardMs = hasSound ? (Date.parse(a.timestamp || a.last_updated || '') || Date.parse(sound.last_updated)) : null;
    const conf = typeof a.confidence === 'number' ? Math.round(a.confidence * 100) : null;

    const hero = hasSound
      ? `<div class="hero ${isActive ? 'on' : ''}" data-entity="${aeEsc(dev.entities.last_sound)}" role="button" tabindex="0">
          <div class="lbl">Last sound</div>
          <div class="sound">${aeEsc(sound.state)}</div>
          <div class="meta">
            ${a.flow_name ? `<span class="chip flow"><ha-icon icon="mdi:waves"></ha-icon>${aeEsc(a.flow_name)}</span>` : ''}
            ${conf != null ? `<span class="chip"><span class="bar"><i style="width:${conf}%"></i></span>${conf}%</span>` : ''}
            ${heardMs ? `<span class="chip"><ha-icon icon="mdi:clock-outline"></ha-icon>${aeAgo(heardMs, now)}</span>` : ''}
          </div>
        </div>`
      : `<div class="hero empty"><div class="lbl">Last sound</div><div class="sound muted">Nothing heard yet</div></div>`;

    const setup = !connected
      ? `<div class="setup">
          <p><b>Connect the AllEars app</b></p>
          <ol>
            <li>Open <b>Configure</b> on the AllEars integration and copy the webhook URL.</li>
            <li>In AllEars, open a flow, add the <b>Trigger Webhook</b> action and paste it.</li>
            <li>In AllEars Settings, tap <b>Sync Flows with Home Assistant</b>.</li>
          </ol>
          ${admin ? '<button class="btn" data-nav="/config/integrations/integration/allears">Open integration</button>' : ''}
        </div>`
      : '';

    const counts = {};
    for (const r of this._history) counts[r.flow] = (counts[r.flow] || 0) + 1;
    if (this._filter !== AE_ALL_FLOWS && !flows.includes(this._filter)) this._filter = AE_ALL_FLOWS;
    const flowChips = flows.length
      ? `<div class="sec"><div class="sec-h">Flows <span class="muted">${flows.length}</span></div>
          <div class="flows">
            ${[AE_ALL_FLOWS, ...flows].map((f) => `<button class="fchip ${f === this._filter ? 'sel' : ''}" data-flow="${aeEsc(f)}">${aeEsc(f)}${f !== AE_ALL_FLOWS && counts[f] ? `<span class="n">${counts[f]}</span>` : ''}</button>`).join('')}
          </div></div>`
      : '';

    let history = '';
    if (this._config.show_history) {
      const rows = this._history.filter((r) => this._filter === AE_ALL_FLOWS || r.flow === this._filter).slice(0, 8);
      history = `<div class="sec"><div class="sec-h">Recent <span class="muted">last ${aeEsc(this._config.history_hours)} h</span></div>
        ${rows.length
          ? `<ul class="list">${rows.map((r) => `<li>
              <ha-icon icon="mdi:microphone"></ha-icon>
              <div class="li-main"><div class="li-s">${aeEsc(r.sound)}</div><div class="li-f muted">${aeEsc(r.flow || '—')}${r.confidence != null ? ` · ${Math.round(r.confidence * 100)}%` : ''}</div></div>
              <div class="li-t muted">${aeAgo(r.t, now)}</div></li>`).join('')}</ul>`
          : `<div class="muted small">No sounds ${this._filter === AE_ALL_FLOWS ? '' : `from ${aeEsc(this._filter)} `}in this period.</div>`}
      </div>`;
    }

    const actions = admin
      ? `<div class="actions">
          <button class="btn" data-act="test"><ha-icon icon="mdi:play-circle-outline"></ha-icon>Send test sound</button>
          <button class="btn" data-nav="/config/devices/device/${aeEsc(dev.id)}"><ha-icon icon="mdi:robot-outline"></ha-icon>Automate</button>
          <button class="btn ghost" data-act="clear" title="Forget the last sound"><ha-icon icon="mdi:eraser"></ha-icon></button>
        </div>`
      : '';

    this.shadowRoot.innerHTML = `<style>${AE_STYLES}</style>
      <ha-card><div class="wrap">
        ${this._header(title, mode, status)}
        ${hero}
        ${setup}
        ${flowChips}
        ${history}
        ${actions}
      </div></ha-card>`;
    this._bind(dev);
  }

  _bind(dev) {
    const root = this.shadowRoot;
    root.querySelectorAll('[data-nav]').forEach((b) =>
      b.addEventListener('click', () => {
        history.pushState(null, '', b.dataset.nav);
        window.dispatchEvent(new CustomEvent('location-changed', { bubbles: true, composed: true }));
      }));
    root.querySelectorAll('[data-flow]').forEach((b) =>
      b.addEventListener('click', () => {
        this._filter = b.dataset.flow;
        this._lastKey = '';
        this._update(true);
      }));
    root.querySelector('[data-act="test"]')?.addEventListener('click', (ev) => {
      ev.currentTarget.disabled = true;
      this._hass.callService(AE_DOMAIN, 'test_webhook', { device_id: dev.id });
    });
    root.querySelector('[data-act="clear"]')?.addEventListener('click', () =>
      this._hass.callService(AE_DOMAIN, 'clear_history', { device_id: dev.id }));
    root.querySelectorAll('[data-entity]').forEach((b) =>
      b.addEventListener('click', () =>
        this.dispatchEvent(new CustomEvent('hass-more-info', { bubbles: true, composed: true, detail: { entityId: b.dataset.entity } }))));
  }
}

class AllEarsCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement('ha-form');
      this._form.computeLabel = (s) => ({
        device_id: 'AllEars phone',
        title: 'Title (optional)',
        show_history: 'Show recent sounds',
        history_hours: 'History window (hours)',
      }[s.name] || s.name);
      this._form.addEventListener('value-changed', (ev) => {
        const config = { ...this._config, ...ev.detail.value };
        Object.keys(config).forEach((k) => (config[k] === '' || config[k] == null) && delete config[k]);
        this._config = config;
        this.dispatchEvent(new CustomEvent('config-changed', { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { show_history: true, history_hours: 24, ...this._config };
    this._form.schema = [
      { name: 'device_id', selector: { device: { integration: AE_DOMAIN } } },
      { name: 'title', selector: { text: {} } },
      { name: 'show_history', selector: { boolean: {} } },
      { name: 'history_hours', selector: { number: { min: 1, max: 168, mode: 'box', unit_of_measurement: 'h' } } },
    ];
  }
}

const AE_STYLES = `
  :host { display: block; }
  ha-card { display: block; overflow: hidden; }
  .wrap > * { min-width: 0; }
  .wrap { padding: 16px; display: grid; gap: 14px; }
  .muted { color: var(--secondary-text-color); }
  .small { font-size: 13px; }
  .head { display: flex; align-items: center; gap: 12px; }
  .ear { position: relative; width: 44px; height: 44px; flex: none; border-radius: 50%;
    display: grid; place-items: center; background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); color: var(--primary-color); }
  .ear.active { background: rgba(var(--rgb-warning-color, 255, 166, 0), .16); color: var(--warning-color, #ffa600); }
  .ear.off { background: var(--secondary-background-color); color: var(--disabled-text-color, #999); }
  .ear ha-icon { --mdc-icon-size: 24px; position: relative; }
  .ring { position: absolute; inset: 0; border-radius: 50%; border: 2px solid currentColor; opacity: 0; }
  .ear.active .ring { animation: ae-ping 1.6s ease-out infinite; }
  .ear.active .r2 { animation-delay: .8s; }
  @keyframes ae-ping { 0% { transform: scale(.9); opacity: .55; } 100% { transform: scale(1.6); opacity: 0; } }
  @media (prefers-reduced-motion: reduce) { .ear.active .ring { animation: none; opacity: .4; } }
  .ttl { min-width: 0; }
  .name { font-size: 17px; font-weight: 500; line-height: 1.25; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .status { font-size: 13px; color: var(--secondary-text-color); }
  .status.active { color: var(--warning-color, #ffa600); font-weight: 500; }
  .hero { border-radius: 12px; padding: 14px; background: var(--secondary-background-color); display: grid; gap: 6px; transition: background .3s; }
  .hero[data-entity] { cursor: pointer; }
  .hero.on { background: rgba(var(--rgb-warning-color, 255, 166, 0), .14); }
  .lbl { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--secondary-text-color); }
  .sound { font-size: 24px; font-weight: 500; line-height: 1.2; overflow-wrap: anywhere; }
  .sound.muted { font-size: 17px; font-weight: 400; }
  .meta { display: flex; flex-wrap: wrap; gap: 6px; }
  .chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; padding: 3px 9px; border-radius: 999px;
    background: var(--card-background-color, #fff); color: var(--primary-text-color); }
  .chip ha-icon { --mdc-icon-size: 15px; color: var(--secondary-text-color); }
  .chip.flow ha-icon { color: var(--primary-color); }
  .bar { width: 34px; height: 5px; border-radius: 3px; background: var(--divider-color); overflow: hidden; display: inline-block; }
  .bar i { display: block; height: 100%; background: var(--primary-color); }
  .sec { display: grid; gap: 8px; }
  .sec-h { font-size: 13px; font-weight: 500; display: flex; gap: 6px; align-items: baseline; }
  .flows { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; padding-bottom: 2px; }
  .flows::-webkit-scrollbar { display: none; }
  .fchip { flex: none; font: inherit; font-size: 13px; cursor: pointer; padding: 5px 12px; border-radius: 999px;
    border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); display: inline-flex; gap: 6px; align-items: center; }
  .fchip.sel { border-color: var(--primary-color); background: rgba(var(--rgb-primary-color, 3, 169, 244), .12); font-weight: 500; }
  .fchip .n { font-size: 11px; min-width: 18px; padding: 0 5px; border-radius: 9px; background: var(--secondary-background-color); text-align: center; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; }
  .list li { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 8px 0; border-top: 1px solid var(--divider-color); }
  .list li:first-child { border-top: 0; }
  .list ha-icon { --mdc-icon-size: 18px; color: var(--secondary-text-color); }
  .li-s { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .li-f { font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .li-t { font-size: 12.5px; white-space: nowrap; }
  .setup { border: 1px dashed var(--divider-color); border-radius: 12px; padding: 12px 14px; font-size: 14px; display: grid; gap: 6px; }
  .setup p { margin: 0; }
  .setup ol { margin: 0; padding-left: 20px; display: grid; gap: 4px; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn { font: inherit; font-size: 14px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    min-height: 36px; padding: 0 14px; border-radius: 18px; border: 1px solid var(--divider-color);
    background: transparent; color: var(--primary-color); flex: 1 1 auto; }
  .btn ha-icon { --mdc-icon-size: 18px; }
  .btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
  .btn.ghost { flex: 0 0 auto; color: var(--secondary-text-color); }
  .btn:disabled { opacity: .5; cursor: default; }
  .btn:focus-visible, .fchip:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
`;

if (!customElements.get('all-ears-card')) customElements.define('all-ears-card', AllEarsCard);
if (!customElements.get('all-ears-card-editor')) customElements.define('all-ears-card-editor', AllEarsCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === 'all-ears-card')) {
  window.customCards.push({
    type: 'all-ears-card',
    name: 'AllEars',
    preview: true,
    description: 'Live sound status, last sound, flows and recent history from an AllEars phone.',
    documentationURL: 'https://github.com/cliqueraft/allears-hacs-plugin',
  });
}
console.info(`%c ALLEARS-CARD %c ${AE_VERSION} `, 'background:#03a9f4;color:#fff;border-radius:3px 0 0 3px', 'background:#444;color:#fff;border-radius:0 3px 3px 0');
