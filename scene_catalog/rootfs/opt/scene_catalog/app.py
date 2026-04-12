import html
import json
import math
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

HOST = "0.0.0.0"
PORT = 8099

SCENES = {
    "golden_lounge": {
        "name": "Golden Lounge",
        "brightness": 155,
        "transition": 1,
        "palette": [
            [0.585, 0.385],
            [0.54, 0.405],
            [0.502, 0.415],
        ],
    },
    "coastal_breeze": {
        "name": "Coastal Breeze",
        "brightness": 185,
        "transition": 1,
        "palette": [
            [0.28, 0.29],
            [0.24, 0.26],
            [0.21, 0.22],
            [0.33, 0.34],
        ],
    },
    "studio_focus": {
        "name": "Studio Focus",
        "xy_color": [0.368, 0.3686],
        "brightness": 254,
        "transition": 1,
        "palette": [
            [0.37, 0.37],
            [0.34, 0.36],
            [0.39, 0.39],
        ],
    },
    "sunset_ribbon": {
        "name": "Sunset Ribbon",
        "brightness": 170,
        "transition": 2,
        "palette": [
            [0.62, 0.35],
            [0.57, 0.37],
            [0.53, 0.39],
            [0.49, 0.41],
        ],
    },
    "aurora_flow": {
        "name": "Aurora Flow (Dynamic)",
        "brightness": 170,
        "transition": 5,
        "dynamic_interval": 7,
        "dynamic_step": 0.65,
        "palette": [
            [0.17, 0.18],
            [0.22, 0.29],
            [0.31, 0.21],
            [0.37, 0.28],
            [0.45, 0.24],
        ],
    },
    "prism_drift": {
        "name": "Prism Drift (Dynamic)",
        "brightness": 165,
        "transition": 6,
        "dynamic_interval": 8,
        "dynamic_step": 0.8,
        "palette": [
            [0.63, 0.34],
            [0.51, 0.41],
            [0.43, 0.45],
            [0.34, 0.33],
            [0.24, 0.25],
        ],
    },
}


class DynamicSceneRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._active = {
            "running": False,
            "scene_key": None,
            "entity_ids": [],
            "interval": 0,
            "transition": None,
        }

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._active["running"],
                "scene_key": self._active["scene_key"],
                "entity_ids": list(self._active["entity_ids"]),
                "interval": self._active["interval"],
                "transition": self._active["transition"],
            }

    def stop(self) -> bool:
        with self._lock:
            if not self._active["running"]:
                return False
            self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=2)

        with self._lock:
            self._active = {
                "running": False,
                "scene_key": None,
                "entity_ids": [],
                "interval": 0,
                "transition": None,
            }
            self._thread = None
            self._stop_event.clear()

        return True

    def start(self, scene_key: str, entity_ids: list[str], interval: int, transition: int | None):
        self.stop()

        with self._lock:
            self._active = {
                "running": True,
                "scene_key": scene_key,
                "entity_ids": list(entity_ids),
                "interval": interval,
                "transition": transition,
            }

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        frame = 0
        while not self._stop_event.is_set():
            with self._lock:
                scene_key = self._active["scene_key"]
                entity_ids = list(self._active["entity_ids"])
                interval = max(1, int(self._active["interval"]))
                transition = self._active["transition"]

            try:
                apply_scene_to_entities(entity_ids, scene_key, dynamic=True, frame=frame, transition_override=transition)
            except Exception as err:
                print(f"Dynamic scene error: {err}", flush=True)

            frame += 1
            if self._stop_event.wait(interval):
                break


DYNAMIC_RUNNER = DynamicSceneRunner()


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


def scene_palette_color(palette: list[list[float]], index: int, total: int, phase: float = 0.0) -> list[float]:
    if not palette:
        return [0.35, 0.35]

    if total <= 1:
        return palette[int(math.floor(phase)) % len(palette)]

    spread = (index / total) * len(palette)
    palette_index = int(math.floor(spread + phase)) % len(palette)
    return palette[palette_index]


def apply_scene_to_entities(
    entity_ids: list[str],
    scene_key: str,
    dynamic: bool = False,
    frame: int = 0,
    transition_override: int | None = None,
) -> tuple[int, list[str]]:
    scene = SCENES[scene_key]
    palette = scene.get("palette", [])
    brightness = int(scene.get("brightness", 180))

    base_transition = int(scene.get("transition", 1))
    transition = int(transition_override) if transition_override is not None else base_transition

    phase = 0.0
    if dynamic:
        phase = float(scene.get("dynamic_step", 0.6)) * frame

    success = 0
    errors = []

    for idx, entity_id in enumerate(entity_ids):
        color = scene_palette_color(palette, idx, len(entity_ids), phase=phase)

        payload = {
            "entity_id": entity_id,
            "xy_color": color,
            "brightness": brightness,
            "transition": transition,
        }

        req = Request(
            "http://supervisor/core/api/services/light/turn_on",
            data=json.dumps(payload).encode("utf-8"),
            headers=core_api_headers(),
            method="POST",
        )

        try:
            with urlopen(req, timeout=15) as resp:
                if 200 <= resp.status < 300:
                    success += 1
                else:
                    errors.append(f"{entity_id}: status {resp.status}")
        except Exception as err:
            errors.append(f"{entity_id}: {err}")

    return success, errors


def parse_positive_int(value: str, default_value: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default_value
    except Exception:
        return default_value


class Handler(BaseHTTPRequestHandler):
    @staticmethod
    def _request_path(raw_path: str) -> str:
        return urlparse(raw_path).path

    def _render(
        self,
        message: str = "",
        selected_targets: list[str] | None = None,
        selected_scene: str | None = None,
        interval_value: int | None = None,
        transition_value: int | None = None,
    ):
        default_targets = os.environ.get("SCENE_CATALOG_DEFAULT_TARGETS", "light.living_room")
        selected_targets = selected_targets or [x.strip() for x in default_targets.split(",") if x.strip()]
        selected_targets_set = set(selected_targets)
        if selected_scene is None:
            selected_scene = next(iter(SCENES.keys()))

        status = DYNAMIC_RUNNER.status()

        scene_options = ""
        for key, data in SCENES.items():
            marker = " (Dynamic)" if "dynamic_interval" in data else ""
            selected_attr = " selected" if key == selected_scene else ""
            scene_options += (
                f"<option value='{html.escape(key)}'{selected_attr}>"
                f"{html.escape(data['name'])}{marker}</option>"
            )

        if interval_value is None:
            interval_value = int(SCENES.get(selected_scene, {}).get("dynamic_interval", 8))
        if transition_value is None:
            transition_value = int(SCENES.get(selected_scene, {}).get("transition", 2))

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
        .status {{ margin-bottom: 12px; font-size: 14px; color: #1f2a44; }}
        .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .actions button {{ margin-top: 0; }}
  </style>
</head>
<body>
  <div class='card'>
    <h2>Scene Catalog</h2>
        <p>Pick a palette scene and target lights. Colors are spread across selected lights.</p>
        <div class='status'>Dynamic status: {html.escape(str(status))}</div>
    <div class='msg'>{html.escape(message)}</div>
                <form method='post' action='apply'>
      <label for='scene'>Scene</label>
      <select name='scene' id='scene'>{scene_options}</select>

      <label for='targets'>Light targets</label>
            {selected_field}
            <div class='warn'>{html.escape(lights_error)}</div>

            <div class='row'>
                <div>
                    <label for='interval'>Dynamic interval (seconds)</label>
                    <input name='interval' id='interval' value='{interval_value}' />
                </div>
                <div>
                    <label for='transition'>Transition (seconds)</label>
                    <input name='transition' id='transition' value='{transition_value}' />
                </div>
            </div>

            <div class='actions'>
                <button type='submit' name='action' value='apply_fixed'>Apply Fixed Scene</button>
                <button type='submit' name='action' value='start_dynamic'>Start Dynamic Scene</button>
                <button type='submit' name='action' value='stop_dynamic'>Stop Dynamic Scene</button>
            </div>
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
        action = (form.get("action", ["apply_fixed"])[0] or "apply_fixed").strip()

        scene = (form.get("scene", [""])[0] or "").strip().lower()
        interval_value = parse_positive_int((form.get("interval", ["8"])[0] or "8").strip(), 8)
        transition_value = parse_positive_int((form.get("transition", ["2"])[0] or "2").strip(), 2)

        if action == "stop_dynamic":
            stopped = DYNAMIC_RUNNER.stop()
            msg = "Dynamic scene stopped." if stopped else "No dynamic scene was running."
            self._render(msg, interval_value=interval_value, transition_value=transition_value)
            return

        if scene not in SCENES:
            self._render(
                "Unknown scene selected.",
                selected_scene=scene,
                interval_value=interval_value,
                transition_value=transition_value,
            )
            return

        raw_targets = [x.strip() for x in form.get("targets", []) if x.strip()]
        if len(raw_targets) == 1 and "," in raw_targets[0]:
            entity_ids = [x.strip() for x in raw_targets[0].split(",") if x.strip()]
        else:
            entity_ids = raw_targets

        if not entity_ids:
            self._render(
                "Please select at least one light.",
                selected_scene=scene,
                interval_value=interval_value,
                transition_value=transition_value,
            )
            return

        if not supervisor_token():
            self._render(
                "SUPERVISOR_TOKEN missing. Enable Home Assistant API access in app config.",
                selected_targets=entity_ids,
                selected_scene=scene,
                interval_value=interval_value,
                transition_value=transition_value,
            )
            return

        try:
            if action == "start_dynamic":
                DYNAMIC_RUNNER.start(scene, entity_ids, interval_value, transition_value)
                self._render(
                    f"Started dynamic scene '{SCENES[scene]['name']}' on {', '.join(entity_ids)}",
                    selected_targets=entity_ids,
                    selected_scene=scene,
                    interval_value=interval_value,
                    transition_value=transition_value,
                )
            else:
                success, errors = apply_scene_to_entities(
                    entity_ids,
                    scene,
                    dynamic=False,
                    transition_override=transition_value,
                )

                if errors:
                    self._render(
                        f"Applied on {success}/{len(entity_ids)} lights. Errors: {' | '.join(errors)}",
                        selected_targets=entity_ids,
                        selected_scene=scene,
                        interval_value=interval_value,
                        transition_value=transition_value,
                    )
                else:
                    self._render(
                        f"Applied '{SCENES[scene]['name']}' on {success} lights.",
                        selected_targets=entity_ids,
                        selected_scene=scene,
                        interval_value=interval_value,
                        transition_value=transition_value,
                    )
        except Exception as err:
            self._render(
                f"Unexpected error: {err}",
                selected_targets=entity_ids,
                selected_scene=scene,
                interval_value=interval_value,
                transition_value=transition_value,
            )


if __name__ == "__main__":
    print("Starting Scene Catalog app on port 8099", flush=True)
    server = HTTPServer((HOST, PORT), Handler)
    server.serve_forever()
