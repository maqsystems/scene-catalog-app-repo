import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from urllib.request import Request, urlopen

HOST = "0.0.0.0"
PORT = 8099

SCENES = {
    "relax": {
        "name": "Relax",
        "xy_color": [0.5019, 0.4152],
        "brightness": 143,
        "transition": 1,
    },
    "focus": {
        "name": "Focus",
        "xy_color": [0.368, 0.3686],
        "brightness": 254,
        "transition": 1,
    },
    "sunset": {
        "name": "Sunset",
        "xy_color": [0.5805, 0.3899],
        "brightness": 180,
        "transition": 2,
    },
}


def supervisor_token() -> str:
    return os.environ.get("SUPERVISOR_TOKEN", "")


def api_call_light_turn_on(entity_ids: list[str], scene_key: str):
    scene = SCENES[scene_key]
    payload = {
        "entity_id": entity_ids,
        "xy_color": scene["xy_color"],
        "brightness": scene["brightness"],
        "transition": scene["transition"],
    }

    req = Request(
        "http://supervisor/core/api/services/light/turn_on",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {supervisor_token()}",
        },
        method="POST",
    )

    with urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def _render(self, message: str = ""):
        default_targets = os.environ.get("SCENE_CATALOG_DEFAULT_TARGETS", "light.living_room")

        scene_options = "".join(
            f"<option value='{k}'>{html.escape(v['name'])}</option>" for k, v in SCENES.items()
        )

        body = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>Scene Catalog</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; max-width: 760px; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 16px; }}
    label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
    input, select {{ width: 100%; padding: 10px; }}
    button {{ margin-top: 16px; padding: 10px 14px; cursor: pointer; }}
    .msg {{ margin-bottom: 12px; color: #1f6f3d; }}
  </style>
</head>
<body>
  <div class='card'>
    <h2>Scene Catalog</h2>
    <p>Pick a scene and target lights (comma-separated entity ids).</p>
    <div class='msg'>{html.escape(message)}</div>
    <form method='post' action='/apply'>
      <label for='scene'>Scene</label>
      <select name='scene' id='scene'>{scene_options}</select>

      <label for='targets'>Light targets</label>
      <input name='targets' id='targets' value='{html.escape(default_targets)}' />

      <button type='submit'>Apply Scene</button>
    </form>
  </div>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        if self.path == "/":
            self._render()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/apply":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)

        scene = (form.get("scene", [""])[0] or "").strip().lower()
        targets = (form.get("targets", [""])[0] or "").strip()

        if scene not in SCENES:
            self._render("Unknown scene selected.")
            return

        entity_ids = [x.strip() for x in targets.split(",") if x.strip()]
        if not entity_ids:
            self._render("Please provide at least one light entity id.")
            return

        if not supervisor_token():
            self._render("SUPERVISOR_TOKEN missing. Enable Home Assistant API access in app config.")
            return

        try:
            status, _ = api_call_light_turn_on(entity_ids, scene)
            if 200 <= status < 300:
                self._render(f"Applied '{SCENES[scene]['name']}' to {', '.join(entity_ids)}")
            else:
                self._render(f"Call failed with status {status}")
        except HTTPError as err:
            self._render(f"Home Assistant API error: {err.code}")
        except URLError as err:
            self._render(f"Network error: {err.reason}")
        except Exception as err:
            self._render(f"Unexpected error: {err}")


if __name__ == "__main__":
    print("Starting Scene Catalog app on port 8099", flush=True)
    server = HTTPServer((HOST, PORT), Handler)
    server.serve_forever()
