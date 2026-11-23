# AllEars card: how it is wired

* **Served and loaded automatically.** `__init__.py` serves `www/` at `/all-ears-card/`
  (`async_register_static_paths`, falling back to `register_static_path` before HA 2024.7)
  and registers the card with `frontend.add_extra_js_url`, so there is no dashboard resource to add.
* **No hard-coded entity ids.** The card reads `hass.entities` and `hass.devices`, keeps the
  entities whose platform is `allears`, groups them by device and matches each by its
  `translation_key` (`last_sound`, `last_flow`, `sound_active`, `active_flow_filter`, `last_seen`).
* **History** comes from `history/history_during_period` for the *Last sound* entity (with
  attributes), so it survives reloads. Live changes are appended as they arrive.
* **Visual editor**: `all-ears-card-editor` uses `ha-form` with a device selector limited to AllEars.
* **Escaping**: every value from the phone (sound and flow names) is HTML-escaped before rendering.
* **Local preview**: run `python -m http.server` in the repo root and open `/preview.html`.
