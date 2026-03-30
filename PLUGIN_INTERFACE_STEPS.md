# How the Home Assistant Interface Works

With the latest updates, the Lovelace card interface (`all-ears-card.js`) is automatically served directly by the backend Python integration! 

### Step 1: Register the Dashboard Resource
Since the integration serves the file for you, you simply have to tell your Home Assistant dashboard where to find it.

*   **In the HA UI:** Go to **Settings** → **Dashboards** → **Resources** (top right menu) → **Add Resource**.
*   **Enter the URL:** `/all-ears-card/all-ears-card.js`
*   **Type:** JavaScript Module

### Step 2: Use the Visual Editor
You no longer have to guess YAML configurations.
*   Go to any dashboard, click **Edit Dashboard**, then click **Add Card**.
*   Scroll down or search for **AllEars Sound Tracker**.
*   A complete visual editor will open, letting you set the Device Name, adjust toggles, and see a live preview.

### Under the Hood
*   **`__init__.py`:** Automatically maps the `/all-ears-card/` URL path to the integration's internal `www/` directory.
*   **`static getStubConfig()`:** Allows the Home Assistant visual editor to provide default settings when you click the card in the menu.
*   **Data Contract:** The JavaScript still directly reads the states of `sensor.allears_last_detected_sound` and `binary_sensor.allears_sound_active`.
