# How to "Plug In" your Home Assistant Interface

Follow these 4 steps to integrate your existing `all-ears-card.js` into a real Home Assistant environment:

### Step 1: Tell Home Assistant the JS File Exists
Home Assistant doesn't "know" about your JavaScript file just because it’s in a folder. You have to register it as a **Dashboard Resource**.

*   **In the HA UI:** Go to **Settings** → **Dashboards** → **Resources** (top right menu) → **Add Resource**.
*   **Enter the Path:** Enter the path to your file (usually `/local/allears/all-ears-card.js`).

### Step 2: The "Data Contract" (Naming Entities)
Your `all-ears-card.js` expects specific entity IDs (like `binary_sensor.allears_sound_active`).

*   **In your Python Integration:** In files like `sensor.py` or `binary_sensor.py`, you must ensure your logic creates entities with these exact names.
*   **The Bridge:** When the Python code updates a sensor value in the database, the JS card automatically sees that update through the `hass` data object.

### Step 3: Deployment via HACS (Optional but Recommended)
If you want others to "one-click install" your interface, use the `hacs.json` file.

*   **Automation:** This file tells HACS: *"When the user installs AllEars, please move the `all-ears-card.js` file into the `www/` folder and register it as a resource automatically."*

### Step 4: Configuration UI
The "final boss" is allowing the user to configure the card visually without typing YAML.

*   **`static getConfigElement()`:** In your JS class, you can add this method. 
*   **Settings Panel:** This points to a second JS class (an editor) that acts as the "Settings Panel" for your card. Without this, users just edit the YAML configuration directly.
