# Wand TFLite Server

A small TensorFlow Lite server for the Magic Caster Wand integration's Spell Tracking.

## Setup

1. Start the add-on, then click **Open Web UI**.
2. Upload your `.tflite` file. It is saved as `model.tflite`, the name the wand integration asks for.
3. In **Settings → Devices & services → Magic Caster Wand → Configure**, set
   **TFLite Server URL** to:

   `http://local-wand-tflite:8000`

4. Turn on the wand's **Connect** switch, then **Spell Tracking**.

Models are stored in `/addon_configs/local_wand_tflite/models/`, so you can also copy a model there over Samba.

## API

Same as the hass-tflite add-on: `GET /api/health`, `POST /api/initialize`, `POST /api/invoke`,
`GET /api/models`, `PUT /api/models/<name>`, `DELETE /api/models/<name>`.
