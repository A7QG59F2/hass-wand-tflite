# Wand TFLite Server (Home Assistant add-on)

A small TensorFlow Lite inference server for the
[Magic Caster Wand integration](https://github.com/eigger/hass-magic-caster-wand)'s Spell Tracking.
Drop-in replacement for the hass-tflite add-on's API (`/api/health`, `/api/initialize`, `/api/invoke`, model upload).

No model is included. Upload your own `model.tflite` from the add-on's web UI.

## Install

Add this repository in **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, or copy the
`wand_tflite` folder into your `/addons` share and install it from **Local add-ons**.

Then set the integration's **TFLite Server URL** to the add-on's hostname, port 8000
(`http://local-wand-tflite:8000` when installed as a local add-on).

See [wand_tflite/DOCS.md](wand_tflite/DOCS.md).
