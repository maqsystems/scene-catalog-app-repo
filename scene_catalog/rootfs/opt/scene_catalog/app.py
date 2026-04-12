import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
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


def core_api_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {supervisor_token()}",
    }


def get_light_entities() -> list[dict]:
    req = Request(
        "http://supervisor/core/api/states",
        headers=core_api_headers(),
        method="GET",
    )

    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    lights = []
    for state in data:
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith("light."):
            continue

        friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
        lights.append({"entity_id": entity_id, "name": friendly_name})

    lights.sort(key=lambda item: item["name"].lower())
    return lights


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
        headers=core_api_headers(),
        method="POST",
    )

    with urlopen(req, timeout=15) as resp:
        return resp.status, resp.read().decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    @staticmethod
    def _request_path(raw_path: str) -> str:
        return urlparse(raw_path).path

    def _render(self, message: str = "", selected_targets: list[str] | None = None):
        default_targets = os.environ.get("SCENE_CATALOG_DEFAULT_TARGETS", "light.living_room")
        selected_targets = selected_targets or [x.strip() for x in default_targets.split(",") if x.strip()]
        selected_targets_set = set(selected_targets)

        scene_options = "".join(
            f"<option value='{k}'>{html.escape(v['name'])}</option>" for k, v in SCENES.items()
        )

        lights = []
        lights_error = ""
        if supervisor_token():
            try:
                lights = get_light_entities()
            except Exception as err:
                lights_error = f"Could not load lights from Home Assistant: {err}"
        else:
            lights_error = "SUPERVISOR_TOKEN missing. Enable Home Assistant API access in app config."

        selected_field = ""
        if lights:
            options = []
            for light in lights:
                entity_id = light["entity_id"]
                selected_attr = " selected" if entity_id in selected_targets_set else ""
                options.append(
                    f"<option value='{html.escape(entity_id)}'{selected_attr}>"
                    f"{html.escape(light['name'])} ({html.escape(entity_id)})</option>"
                )

            selected_field = (
                "<select name='targets' id='targets' multiple size='10'>"
                + "".join(options)
                + "</select>"
            )
        else:
            selected_field = (
                f"<input name='targets' id='targets' value='{html.escape(default_targets)}' "
                "placeholder='light.living_room, light.bedroom' />"
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
        .warn {{ margin-top: 8px; color: #a15b00; }}
  </style>
</head>
<body>
  <div class='card'>
    <h2>Scene Catalog</h2>
        <p>Pick a scene and target lights.</p>
    <div class='msg'>{html.escape(message)}</div>
        <form method='post' action='apply'>
      <label for='scene'>Scene</label>
      <select name='scene' id='scene'>{scene_options}</select>

      <label for='targets'>Light targets</label>
            {selected_field}
            <div class='warn'>{html.escape(lights_error)}</div>

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
        path = self._request_path(self.path)
        if path == "/" or path.endswith("/"):
            self._render()
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = self._request_path(self.path)
        if not path.endswith("/apply"):
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)

        scene = (form.get("scene", [""])[0] or "").strip().lower()

        if scene not in SCENES:
            self._render("Unknown scene selected.")
            return

        raw_targets = [x.strip() for x in form.get("targets", []) if x.strip()]
        if len(raw_targets) == 1 and "," in raw_targets[0]:
            entity_ids = [x.strip() for x in raw_targets[0].split(",") if x.strip()]
        else:
            entity_ids = raw_targets

        if not entity_ids:
            self._render("Please select at least one light.")
            return

        if not supervisor_token():
            self._render("SUPERVISOR_TOKEN missing. Enable Home Assistant API access in app config.")
            return

        try:
            status, _ = api_call_light_turn_on(entity_ids, scene)
            if 200 <= status < 300:
                self._render(
                    f"Applied '{SCENES[scene]['name']}' to {', '.join(entity_ids)}",
                    selected_targets=entity_ids,
                )
            else:
                self._render(f"Call failed with status {status}", selected_targets=entity_ids)
        except HTTPError as err:
            self._render(f"Home Assistant API error: {err.code} {err.reason}", selected_targets=entity_ids)
        except URLError as err:
            self._render(f"Network error: {err.reason}", selected_targets=entity_ids)
        except Exception as err:
            self._render(f"Unexpected error: {err}", selected_targets=entity_ids)


if __name__ == "__main__":
    print("Starting Scene Catalog app on port 8099", flush=True)
    server = HTTPServer((HOST, PORT), Handler)
    server.serve_forever()
