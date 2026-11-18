"""Small TFLite inference server for the Magic Caster Wand integration.

Speaks the same API as the hass-tflite add-on:
  GET  /api/health
  POST /api/initialize   {"model": "model.tflite"}
  POST /api/invoke       {"model": "model.tflite", "input": [[...]]}
  GET  /api/models
  PUT  /api/models/<name>    (raw .tflite bytes)
  DELETE /api/models/<name>
Plus a small upload page at / (shown in the Home Assistant sidebar).
"""

import hashlib
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from ai_edge_litert.interpreter import Interpreter

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/config/models"))
PORT = int(os.environ.get("PORT", "8000"))
MAX_UPLOAD = 200 * 1024 * 1024
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+\.tflite$")

_lock = threading.Lock()
_cache: dict[str, tuple[float, Interpreter]] = {}
_stats = {"start": time.time(), "invokes": 0}


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def model_path(name: str) -> Path:
    if not name or not NAME_RE.match(name):
        raise ValueError(f"Invalid model name: {name!r} (must end in .tflite)")
    return MODEL_DIR / name


def load(name: str) -> Interpreter:
    """Load (or reuse) an interpreter. Caller must hold _lock."""
    path = model_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"Model not found: {name}. Upload it on the add-on page.")
    mtime = path.stat().st_mtime
    cached = _cache.get(name)
    if cached and cached[0] == mtime:
        return cached[1]
    log(f"Loading model {name}")
    interp = Interpreter(model_path=str(path))
    interp.allocate_tensors()
    _cache[name] = (mtime, interp)
    return interp


def describe(interp: Interpreter) -> dict:
    def info(details):
        return [
            {"index": d["index"], "shape": [int(x) for x in d["shape"]], "dtype": np.dtype(d["dtype"]).name}
            for d in details
        ]

    return {"inputs": info(interp.get_input_details()), "outputs": info(interp.get_output_details())}


def invoke(name: str, body: dict) -> dict:
    with _lock:
        interp = load(name)
        in_details = interp.get_input_details()

        if "inputs" in body:
            items = [(d.get("index", i), d.get("data")) for i, d in enumerate(body["inputs"])]
        elif "input" in body:
            items = [(0, body["input"])]
        else:
            raise ValueError("Request needs 'input' or 'inputs'")

        for pos, data in items:
            if pos >= len(in_details):
                raise ValueError(f"Model has no input #{pos}")
            det = in_details[pos]
            arr = np.asarray(data, dtype=det["dtype"])
            shape = tuple(int(x) for x in det["shape"])
            if arr.shape != shape:
                if arr.size != int(np.prod(shape)):
                    raise ValueError(f"Input #{pos} has shape {list(arr.shape)}, model expects {list(shape)}")
                arr = arr.reshape(shape)
            interp.set_tensor(det["index"], arr)

        interp.invoke()
        _stats["invokes"] += 1
        outputs = []
        for i, det in enumerate(interp.get_output_details()):
            out = interp.get_tensor(det["index"])
            outputs.append(
                {"index": i, "data": out.tolist(), "dtype": out.dtype.name, "shape": list(out.shape)}
            )
        return {"outputs": outputs}


def list_models() -> list:
    models = []
    for p in sorted(MODEL_DIR.glob("*.tflite")):
        data = p.read_bytes()
        models.append({"name": p.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return models


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wand TFLite Server</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem;color:#222}
h1{font-size:1.4rem} .card{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}
table{width:100%;border-collapse:collapse} td{padding:.4rem 0;border-bottom:1px solid #eee;font-size:.9rem}
button{padding:.4rem .8rem;cursor:pointer} .ok{color:#1a7f37} .err{color:#c62828} code{font-size:.85rem}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}.card{border-color:#333}td{border-color:#333}}
</style></head><body>
<h1>Wand TFLite Server</h1>
<div class="card"><b>Status:</b> <span id="status">checking...</span></div>
<div class="card"><b>Upload model</b><br><br>
<input type="file" id="file" accept=".tflite"> <button onclick="upload()">Upload</button>
<p style="font-size:.85rem">The wand integration looks for <code>model.tflite</code>, so the file is saved under that name.</p>
<div id="msg"></div></div>
<div class="card"><b>Installed models</b><table id="models"></table></div>
<script>
async function refresh(){
  try{const h=await fetch('api/health');document.getElementById('status').innerHTML=h.ok?'<span class=ok>running</span>':'error';}
  catch(e){document.getElementById('status').innerHTML='<span class=err>unreachable</span>';}
  const r=await fetch('api/models');const list=await r.json();const t=document.getElementById('models');
  t.innerHTML=list.length?'':'<tr><td>No models yet</td></tr>';
  for(const m of list){const tr=document.createElement('tr');
    tr.innerHTML=`<td>${m.name}</td><td>${(m.size/1024).toFixed(0)} KB</td><td><code>${m.sha256.slice(0,12)}</code></td><td><button>Delete</button></td>`;
    tr.querySelector('button').onclick=async()=>{if(confirm('Delete '+m.name+'?')){await fetch('api/models/'+m.name,{method:'DELETE'});refresh();}};
    t.appendChild(tr);}
}
async function upload(){
  const f=document.getElementById('file').files[0];const msg=document.getElementById('msg');
  if(!f){msg.textContent='Pick a file first.';return;}
  msg.textContent='Uploading...';
  const r=await fetch('api/models/model.tflite',{method:'PUT',body:f});const j=await r.json();
  msg.innerHTML=r.ok?'<span class=ok>Uploaded. Inputs '+JSON.stringify(j.inputs.map(i=>i.shape))+', outputs '+JSON.stringify(j.outputs.map(o=>o.shape))+'</span>':'<span class=err>'+j.error+'</span>';
  refresh();
}
refresh();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "WandTFLite/1.0"

    def log_message(self, fmt, *args):  # quieter access log
        if not self.path.startswith("/api/health"):
            log(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def _send(self, code: int, payload, ctype="application/json"):
        data = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def _route(self):
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def _handle(self, fn):
        try:
            fn()
        except FileNotFoundError as e:
            self._send(404, {"error": str(e)})
        except (ValueError, json.JSONDecodeError) as e:
            self._send(400, {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            log(f"ERROR {type(e).__name__}: {e}")
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        def run():
            route = self._route()
            if route in ("/", "/ui"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            elif route in ("/api/health", "/health"):
                self._send(200, {"status": "ok"})
            elif route == "/api/models":
                self._send(200, list_models())
            elif route == "/api/stats":
                self._send(200, {"uptime_s": int(time.time() - _stats["start"]),
                                 "invoke_count": _stats["invokes"], "cached_models": len(_cache)})
            else:
                self._send(404, {"error": "Not found"})
        self._handle(run)

    def do_POST(self):
        def run():
            route = self._route()
            body = self._json_body()
            name = body.get("model", "model.tflite")
            if route in ("/api/initialize", "/initialize"):
                with _lock:
                    meta = describe(load(name))
                log(f"Initialized {name}: {meta}")
                self._send(200, {"model": name, **meta})
            elif route in ("/api/invoke", "/invoke"):
                self._send(200, invoke(name, body))
            else:
                self._send(404, {"error": "Not found"})
        self._handle(run)

    def do_PUT(self):
        def run():
            route = self._route()
            if not route.startswith("/api/models/"):
                return self._send(404, {"error": "Not found"})
            path = model_path(route.rsplit("/", 1)[1])
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_UPLOAD:
                raise ValueError("Empty or too-large upload")
            data = self.rfile.read(length)
            tmp = path.with_suffix(".upload")
            tmp.write_bytes(data)
            try:
                test = Interpreter(model_path=str(tmp))
                test.allocate_tensors()
                meta = describe(test)
            except Exception as e:  # noqa: BLE001
                tmp.unlink(missing_ok=True)
                raise ValueError(f"Not a valid TFLite model: {e}") from e
            tmp.replace(path)
            with _lock:
                _cache.pop(path.name, None)
            log(f"Saved {path.name} ({len(data)} bytes): {meta}")
            self._send(200, {"model": path.name, **meta})
        self._handle(run)

    def do_DELETE(self):
        def run():
            route = self._route()
            if not route.startswith("/api/models/"):
                return self._send(404, {"error": "Not found"})
            path = model_path(route.rsplit("/", 1)[1])
            if not path.is_file():
                raise FileNotFoundError(f"Model not found: {path.name}")
            path.unlink()
            with _lock:
                _cache.pop(path.name, None)
            self._send(200, {"deleted": path.name})
        self._handle(run)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    found = [p.name for p in MODEL_DIR.glob("*.tflite")]
    log(f"Wand TFLite Server starting on port {PORT}; models in {MODEL_DIR}: {found or 'none yet'}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
