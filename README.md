# Wand TFLite Server (Home Assistant add-on)

A small TensorFlow Lite inference server for the
[Magic Caster Wand integration](https://github.com/eigger/hass-magic-caster-wand)'s Spell Tracking.
Drop-in replacement for the hass-tflite add-on's API (`/api/health`, `/api/initialize`, `/api/invoke`, model upload).

No model is included. Upload your own `model.tflite` from the add-on's web UI.

## Install

[![Open your Home Assistant instance and show the add add-on repository dialog with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FA7QG59F2%2Fhass-wand-tflite)

1. Click the button above, or go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add
   `https://github.com/A7QG59F2/hass-wand-tflite`.
2. Install **Wand TFLite Server**, start it, then click **Open Web UI** and upload your model.
3. In the Magic Caster Wand integration, open **Configure** and set **TFLite Server URL** to:

   `http://f6155c63-wand-tflite:8000`

   (If you copied the `wand_tflite` folder into `/addons` as a local add-on instead, use
   `http://local-wand-tflite:8000`.)

See [wand_tflite/DOCS.md](wand_tflite/DOCS.md).
