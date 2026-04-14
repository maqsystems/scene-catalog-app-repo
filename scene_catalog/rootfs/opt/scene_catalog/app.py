import html
import json
import math
import os
import random
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

HOST = "0.0.0.0"
PORT = 8099
APP_TITLE = "Lighting Scene Studio"
SCENE_CONFIG_DIR = "/config/scene_catalog"
CUSTOM_SCENE_FILE = os.path.join(SCENE_CONFIG_DIR, "custom_scenes.json")

BUILTIN_SCENES = {
    "golden_lounge": {
        "name": "Golden Lounge",
        "kind": "fixed",
        "brightness": 155,
        "transition": 1,
        "palette": [[0.585, 0.385], [0.54, 0.405], [0.502, 0.415]],
        "builder_colors": ["#ffb347", "#ffcc70", "#ffd9a0"],
    },
    "coastal_breeze": {
        "name": "Coastal Breeze",
        "kind": "fixed",
        "brightness": 185,
        "transition": 1,
        "palette": [[0.28, 0.29], [0.24, 0.26], [0.21, 0.22], [0.33, 0.34]],
        "builder_colors": ["#68d8ff", "#86fff7", "#b7e3ff", "#6ea8ff"],
    },
    "studio_focus": {
        "name": "Studio Focus",
        "kind": "fixed",
        "brightness": 254,
        "transition": 1,
        "palette": [[0.37, 0.37], [0.34, 0.36], [0.39, 0.39]],
        "builder_colors": ["#f1f6ff", "#dbe8ff", "#eef2ff"],
    },
    "sunset_ribbon": {
        "name": "Sunset Ribbon",
        "kind": "fixed",
        "brightness": 170,
        "transition": 2,
        "palette": [[0.62, 0.35], [0.57, 0.37], [0.53, 0.39], [0.49, 0.41]],
        "builder_colors": ["#ff7a45", "#ff9661", "#ffb074", "#ffd29c"],
    },
    "emerald_garden": {
        "name": "Emerald Garden",
        "kind": "fixed",
        "brightness": 165,
        "transition": 2,
        "palette": [[0.26, 0.43], [0.24, 0.39], [0.31, 0.45], [0.35, 0.42]],
        "builder_colors": ["#1ec98a", "#4ce0a6", "#78f0bd", "#b2ffd8"],
    },
    "mauve_twilight": {
        "name": "Mauve Twilight",
        "kind": "fixed",
        "brightness": 145,
        "transition": 2,
        "palette": [[0.41, 0.31], [0.45, 0.34], [0.5, 0.36], [0.37, 0.29]],
        "builder_colors": ["#9b7bff", "#c192ff", "#ffb0ea", "#7f5fd6"],
    },
    "arctic_bloom": {
        "name": "Arctic Bloom",
        "kind": "fixed",
        "brightness": 180,
        "transition": 2,
        "palette": [[0.25, 0.27], [0.29, 0.31], [0.33, 0.35], [0.22, 0.24]],
        "builder_colors": ["#bdf5ff", "#dffcff", "#a7d8ff", "#f5fdff"],
    },
    "volcanic_ember": {
        "name": "Volcanic Ember",
        "kind": "fixed",
        "brightness": 175,
        "transition": 2,
        "palette": [[0.67, 0.32], [0.62, 0.34], [0.58, 0.36], [0.53, 0.38]],
        "builder_colors": ["#ff4d00", "#ff6f1a", "#ff9145", "#ffc07a"],
    },
    "forest_mist": {
        "name": "Forest Mist",
        "kind": "fixed",
        "brightness": 150,
        "transition": 3,
        "palette": [[0.29, 0.39], [0.26, 0.37], [0.34, 0.43], [0.31, 0.41]],
        "builder_colors": ["#5ca06b", "#86c58d", "#b4e0be", "#d9f3e1"],
    },
    "aurora_flow": {
        "name": "Aurora Flow",
        "kind": "dynamic",
        "brightness": 170,
        "transition": 5,
        "dynamic_interval": 7,
        "dynamic_step": 0.65,
        "dynamic_transition_range": [3, 8],
        "dynamic_stagger_max": 2.0,
        "palette": [[0.17, 0.18], [0.22, 0.29], [0.31, 0.21], [0.37, 0.28], [0.45, 0.24]],
        "builder_colors": ["#23ffd3", "#44b8ff", "#7b66ff", "#d96cff", "#9dff87"],
    },
    "prism_drift": {
        "name": "Prism Drift",
        "kind": "dynamic",
        "brightness": 165,
        "transition": 6,
        "dynamic_interval": 8,
        "dynamic_step": 0.8,
        "dynamic_transition_range": [4, 10],
        "dynamic_stagger_max": 2.4,
        "palette": [[0.63, 0.34], [0.51, 0.41], [0.43, 0.45], [0.34, 0.33], [0.24, 0.25]],
        "builder_colors": ["#ff934f", "#ffd166", "#ef476f", "#7b61ff", "#56cfe1"],
    },
    "candle_wave": {
        "name": "Candle Wave",
        "kind": "dynamic",
        "brightness": 135,
        "transition": 7,
        "dynamic_interval": 9,
        "dynamic_step": 0.45,
        "dynamic_transition_range": [5, 12],
        "dynamic_stagger_max": 3.0,
        "palette": [[0.62, 0.35], [0.57, 0.37], [0.53, 0.39], [0.5, 0.41], [0.47, 0.42]],
        "builder_colors": ["#ffb86c", "#ffc98e", "#ffd8a8", "#ffefc2", "#ff8c42"],
    },
    "neon_rain": {
        "name": "Neon Rain",
        "kind": "dynamic",
        "brightness": 190,
        "transition": 4,
        "dynamic_interval": 6,
        "dynamic_step": 1.0,
        "dynamic_transition_range": [2, 7],
        "dynamic_stagger_max": 1.4,
        "palette": [[0.17, 0.16], [0.24, 0.2], [0.31, 0.18], [0.4, 0.23], [0.5, 0.3]],
        "builder_colors": ["#00f5ff", "#1aff9c", "#b400ff", "#ff3cac", "#7b61ff"],
    },
    "moon_tide": {
        "name": "Moon Tide",
        "kind": "dynamic",
        "brightness": 140,
        "transition": 7,
        "dynamic_interval": 10,
        "dynamic_step": 0.55,
        "dynamic_transition_range": [5, 14],
        "dynamic_stagger_max": 3.2,
        "palette": [[0.2, 0.24], [0.24, 0.29], [0.29, 0.34], [0.34, 0.38], [0.28, 0.31]],
        "builder_colors": ["#9bbcff", "#bfd4ff", "#d8e2ff", "#8aa4ff", "#7be0ff"],
    },
    "solar_flare": {
        "name": "Solar Flare",
        "kind": "dynamic",
        "brightness": 200,
        "transition": 5,
        "dynamic_interval": 6,
        "dynamic_step": 1.1,
        "dynamic_transition_range": [2, 9],
        "dynamic_stagger_max": 1.8,
        "palette": [[0.69, 0.31], [0.63, 0.33], [0.56, 0.36], [0.49, 0.39], [0.42, 0.34]],
        "builder_colors": ["#ff5e00", "#ff8a00", "#ffb000", "#ffe066", "#ff735c"],
    },
    "deep_ocean_pulse": {
        "name": "Deep Ocean Pulse",
        "kind": "dynamic",
        "brightness": 160,
        "transition": 8,
        "dynamic_interval": 9,
        "dynamic_step": 0.7,
        "dynamic_transition_range": [4, 13],
        "dynamic_stagger_max": 2.8,
        "palette": [[0.18, 0.2], [0.2, 0.24], [0.22, 0.28], [0.25, 0.32], [0.27, 0.35]],
        "builder_colors": ["#004e92", "#0077b6", "#00b4d8", "#48cae4", "#90e0ef"],
    },
}


def ensure_scene_storage() -> None:
    os.makedirs(SCENE_CONFIG_DIR, exist_ok=True)


def load_custom_scenes() -> dict:
    ensure_scene_storage()
    if not os.path.exists(CUSTOM_SCENE_FILE):
        return {}
    try:
        with open(CUSTOM_SCENE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_custom_scene(scene_key: str, scene_data: dict) -> None:
    scenes = load_custom_scenes()
    scenes[scene_key] = scene_data
    ensure_scene_storage()
    with open(CUSTOM_SCENE_FILE, "w", encoding="utf-8") as file:
        json.dump(scenes, file, indent=2)


def delete_custom_scene(scene_key: str) -> bool:
    scenes = load_custom_scenes()
    if scene_key not in scenes:
        return False
    del scenes[scene_key]
    with open(CUSTOM_SCENE_FILE, "w", encoding="utf-8") as file:
        json.dump(scenes, file, indent=2)
    return True


def get_all_scenes() -> dict:
    scenes = dict(BUILTIN_SCENES)
    scenes.update(load_custom_scenes())
    return scenes


def scene_keys(kind: str) -> list[str]:
    return [key for key, value in get_all_scenes().items() if value.get("kind", "fixed") == kind]


def sanitize_scene_key(value: str) -> str:
    value = value.strip().lower().replace(" ", "_")
    value = re.sub(r"[^a-z0-9_]+", "", value)
    return value


def hex_to_xy(hex_color: str) -> list[float]:
    raw = hex_color.strip().lstrip("#")
    if len(raw) != 6:
        return [0.35, 0.35]

    r = int(raw[0:2], 16) / 255.0
    g = int(raw[2:4], 16) / 255.0
    b = int(raw[4:6], 16) / 255.0

    def gamma(value: float) -> float:
        return ((value + 0.055) / 1.055) ** 2.4 if value > 0.04045 else value / 12.92

    r = gamma(r)
    g = gamma(g)
    b = gamma(b)

    x = r * 0.664511 + g * 0.154324 + b * 0.162028
    y = r * 0.283881 + g * 0.668433 + b * 0.047685
    z = r * 0.000088 + g * 0.07231 + b * 0.986039
    total = x + y + z
    if total == 0:
        return [0.35, 0.35]

    return [round(x / total, 4), round(y / total, 4)]


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
    scenes = get_all_scenes()
    scene = scenes[scene_key]
    palette = scene.get("palette", [])
    brightness = int(scene.get("brightness", 180))

    base_transition = float(scene.get("transition", 1))
    transition = float(transition_override) if transition_override is not None else base_transition
    dynamic_range = scene.get("dynamic_transition_range", [transition, transition])
    stagger_max = float(scene.get("dynamic_stagger_max", 0.0)) if dynamic else 0.0

    phase = 0.0
    if dynamic:
        phase = float(scene.get("dynamic_step", 0.6)) * frame

    success = 0
    errors = []

    for idx, entity_id in enumerate(entity_ids):
        color = scene_palette_color(palette, idx, len(entity_ids), phase=phase)

        current_transition = transition
        if dynamic and isinstance(dynamic_range, list) and len(dynamic_range) == 2:
            low = min(float(dynamic_range[0]), float(dynamic_range[1]))
            high = max(float(dynamic_range[0]), float(dynamic_range[1]))
            current_transition = round(random.uniform(low, high), 2)

        payload = {
            "entity_id": entity_id,
            "xy_color": color,
            "brightness": brightness,
            "transition": current_transition,
        }

        try:
            if stagger_max > 0:
                threading.Event().wait(random.uniform(0, stagger_max))

            req = Request(
                "http://supervisor/core/api/services/light/turn_on",
                data=json.dumps(payload).encode("utf-8"),
                headers=core_api_headers(),
                method="POST",
            )

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
        all_scenes = get_all_scenes()
        default_targets = os.environ.get("SCENE_CATALOG_DEFAULT_TARGETS", "light.living_room")
        selected_targets = selected_targets or [x.strip() for x in default_targets.split(",") if x.strip()]
        selected_targets_set = set(selected_targets)
        if selected_scene is None:
            selected_scene = next(iter(all_scenes.keys()), "")

        status = DYNAMIC_RUNNER.status()
        custom_scenes = load_custom_scenes()

        fixed_options = ""
        dynamic_options = ""
        for key, data in all_scenes.items():
            selected_attr = " selected" if key == selected_scene else ""
            option = (
                f"<option value='{html.escape(key)}'{selected_attr}>"
                f"{html.escape(data['name'])} ({html.escape(key)})</option>"
            )
            if data.get("kind", "fixed") == "dynamic":
                dynamic_options += option
            else:
                fixed_options += option

        scene_options = (
            f"<optgroup label='Fixed lighting scenes'>{fixed_options}</optgroup>"
            f"<optgroup label='Dynamic lighting scenes'>{dynamic_options}</optgroup>"
        )

        selected_scene_data = all_scenes.get(selected_scene, {})
        if interval_value is None:
            interval_value = int(selected_scene_data.get("dynamic_interval", 8))
        if transition_value is None:
            transition_value = int(selected_scene_data.get("transition", 2))

        lights = []
        lights_error = ""
        if supervisor_token():
            try:
                lights = get_light_entities()
            except Exception as err:
                lights_error = f"Could not load lights from Home Assistant: {err}"
        else:
            lights_error = "SUPERVISOR_TOKEN missing. Enable Home Assistant API access in app config."

        if lights:
            options = []
            for light in lights:
                entity_id = light["entity_id"]
                selected_attr = " selected" if entity_id in selected_targets_set else ""
                options.append(
                    f"<option value='{html.escape(entity_id)}'{selected_attr}>"
                    f"{html.escape(light['name'])} ({html.escape(entity_id)})</option>"
                )
            selected_field = "<select name='targets' id='targets' multiple size='10'>" + "".join(options) + "</select>"
        else:
            selected_field = (
                f"<input name='targets' id='targets' value='{html.escape(default_targets)}' "
                "placeholder='light.living_room, light.bedroom' />"
            )

        custom_scene_list = "<li>No custom lighting scenes saved yet.</li>"
        if custom_scenes:
            custom_scene_list = "".join(
                f"<li><strong>{html.escape(key)}</strong> — {html.escape(value.get('name', key))} ({html.escape(value.get('kind', 'fixed'))})</li>"
                for key, value in sorted(custom_scenes.items())
            )

        body = f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>{APP_TITLE}</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; max-width: 980px; background: #fafafa; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 18px; background: white; margin-bottom: 18px; }}
    label {{ display: block; margin: 12px 0 6px; font-weight: 600; }}
    input, select {{ width: 100%; padding: 10px; box-sizing: border-box; }}
    input[type='color'] {{ height: 44px; padding: 4px; }}
    button {{ margin-top: 16px; padding: 10px 14px; cursor: pointer; }}
    .msg {{ margin-bottom: 12px; color: #1f6f3d; font-weight: 600; }}
    .warn {{ margin-top: 8px; color: #a15b00; }}
    .status {{ margin-bottom: 12px; font-size: 14px; color: #1f2a44; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .row3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .row5 {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .actions button {{ margin-top: 0; }}
    ul {{ margin: 8px 0 0; padding-left: 20px; }}
    .hint {{ font-size: 13px; color: #555; }}
  </style>
</head>
<body>
  <div class='card'>
    <h2>{APP_TITLE}</h2>
    <p>Pick a lighting scene and target lights. Palette colors are spread across the selected lights.</p>
    <div class='status'>Dynamic status: {html.escape(str(status))}</div>
    <div class='msg'>{html.escape(message)}</div>
    <form method='post' action='apply'>
      <label for='scene'>Lighting scene</label>
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
        <button type='submit' name='action' value='apply_fixed'>Apply Lighting Scene</button>
        <button type='submit' name='action' value='start_dynamic'>Start Dynamic Lighting Scene</button>
        <button type='submit' name='action' value='stop_dynamic'>Stop Dynamic Lighting Scene</button>
      </div>
    </form>
  </div>

  <div class='card'>
    <h2>Lighting Scene Builder</h2>
    <p>Create or modify your own lighting scenes. Reusing the same key updates an existing custom scene.</p>
    <div class='hint'>These custom scenes are stored in /config/scene_catalog/custom_scenes.json and can then be used by the integration services.</div>
    <form method='post' action='manage_scene'>
      <div class='row'>
        <div>
          <label for='scene_key'>Scene key</label>
          <input name='scene_key' id='scene_key' placeholder='my_evening_glow' />
        </div>
        <div>
          <label for='scene_name'>Scene name</label>
          <input name='scene_name' id='scene_name' placeholder='My Evening Glow' />
        </div>
      </div>

      <div class='row3'>
        <div>
          <label for='scene_kind'>Type</label>
          <select name='scene_kind' id='scene_kind'>
            <option value='fixed'>Fixed lighting scene</option>
            <option value='dynamic'>Dynamic lighting scene</option>
          </select>
        </div>
        <div>
          <label for='scene_brightness'>Brightness</label>
          <input name='scene_brightness' id='scene_brightness' value='170' />
        </div>
        <div>
          <label for='scene_transition'>Base transition (seconds)</label>
          <input name='scene_transition' id='scene_transition' value='3' />
        </div>
      </div>

      <div class='row3'>
        <div>
          <label for='scene_interval'>Dynamic interval</label>
          <input name='scene_interval' id='scene_interval' value='8' />
        </div>
        <div>
          <label for='scene_transition_min'>Dynamic transition min</label>
          <input name='scene_transition_min' id='scene_transition_min' value='3' />
        </div>
        <div>
          <label for='scene_transition_max'>Dynamic transition max</label>
          <input name='scene_transition_max' id='scene_transition_max' value='9' />
        </div>
      </div>

      <div class='row'>
        <div>
          <label for='scene_stagger'>Dynamic stagger max (seconds)</label>
          <input name='scene_stagger' id='scene_stagger' value='1.5' />
        </div>
        <div>
          <label for='scene_step'>Dynamic color step</label>
          <input name='scene_step' id='scene_step' value='0.75' />
        </div>
      </div>

      <label>Palette colors</label>
      <div class='row5'>
        <input type='color' name='color_1' value='#ffb347' />
        <input type='color' name='color_2' value='#ffcc70' />
        <input type='color' name='color_3' value='#ffd9a0' />
        <input type='color' name='color_4' value='#ffd29c' />
        <input type='color' name='color_5' value='#fff1d6' />
      </div>

      <div class='actions'>
        <button type='submit' name='builder_action' value='save_scene'>Save / Update Lighting Scene</button>
        <button type='submit' name='builder_action' value='delete_scene'>Delete Lighting Scene</button>
      </div>
    </form>

    <h3>Saved custom lighting scenes</h3>
    <ul>{custom_scene_list}</ul>
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
        if not (path.endswith("/apply") or path.endswith("/manage_scene")):
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw)

        if path.endswith("/manage_scene"):
            builder_action = (form.get("builder_action", ["save_scene"])[0] or "save_scene").strip()
            scene_key = sanitize_scene_key((form.get("scene_key", [""])[0] or "").strip())

            if not scene_key:
                self._render("Please provide a valid custom scene key.")
                return

            if builder_action == "delete_scene":
                deleted = delete_custom_scene(scene_key)
                self._render(
                    f"Deleted lighting scene '{scene_key}'." if deleted else f"No custom lighting scene found for '{scene_key}'."
                )
                return

            scene_name = (form.get("scene_name", [scene_key.replace("_", " ").title()])[0] or scene_key).strip()
            scene_kind = (form.get("scene_kind", ["fixed"])[0] or "fixed").strip().lower()
            brightness = parse_positive_int((form.get("scene_brightness", ["170"])[0] or "170").strip(), 170)
            transition = parse_positive_int((form.get("scene_transition", ["3"])[0] or "3").strip(), 3)
            interval = parse_positive_int((form.get("scene_interval", ["8"])[0] or "8").strip(), 8)
            transition_min = parse_positive_int((form.get("scene_transition_min", ["3"])[0] or "3").strip(), 3)
            transition_max = parse_positive_int((form.get("scene_transition_max", ["9"])[0] or "9").strip(), 9)
            scene_step = max(0.1, float((form.get("scene_step", ["0.75"])[0] or "0.75").strip()))
            scene_stagger = max(0.0, float((form.get("scene_stagger", ["1.5"])[0] or "1.5").strip()))

            builder_colors = []
            for idx in range(1, 6):
                color_value = (form.get(f"color_{idx}", [""])[0] or "").strip()
                if color_value:
                    builder_colors.append(color_value)

            if len(builder_colors) < 2:
                self._render("Please choose at least two colors for the palette.")
                return

            scene_payload = {
                "name": scene_name,
                "kind": scene_kind,
                "brightness": brightness,
                "transition": transition,
                "palette": [hex_to_xy(color) for color in builder_colors],
                "builder_colors": builder_colors,
            }

            if scene_kind == "dynamic":
                low = min(transition_min, transition_max)
                high = max(transition_min, transition_max)
                scene_payload["dynamic_interval"] = interval
                scene_payload["dynamic_step"] = round(scene_step, 2)
                scene_payload["dynamic_transition_range"] = [low, high]
                scene_payload["dynamic_stagger_max"] = round(scene_stagger, 2)

            save_custom_scene(scene_key, scene_payload)
            self._render(f"Saved lighting scene '{scene_name}' as key '{scene_key}'.", selected_scene=scene_key)
            return

        action = (form.get("action", ["apply_fixed"])[0] or "apply_fixed").strip()
        scene = (form.get("scene", [""])[0] or "").strip().lower()
        interval_value = parse_positive_int((form.get("interval", ["8"])[0] or "8").strip(), 8)
        transition_value = parse_positive_int((form.get("transition", ["2"])[0] or "2").strip(), 2)
        all_scenes = get_all_scenes()

        if action == "stop_dynamic":
            stopped = DYNAMIC_RUNNER.stop()
            msg = "Dynamic lighting scene stopped." if stopped else "No dynamic lighting scene was running."
            self._render(msg, interval_value=interval_value, transition_value=transition_value)
            return

        if scene not in all_scenes:
            self._render(
                "Unknown lighting scene selected.",
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

        scene_kind = all_scenes[scene].get("kind", "fixed")
        if action == "start_dynamic" and scene_kind != "dynamic":
            self._render("Please choose a dynamic lighting scene for the dynamic action.", selected_scene=scene)
            return
        if action == "apply_fixed" and scene_kind != "fixed":
            self._render("Please choose a fixed lighting scene for the fixed action.", selected_scene=scene)
            return

        try:
            if action == "start_dynamic":
                DYNAMIC_RUNNER.start(scene, entity_ids, interval_value, transition_value)
                self._render(
                    f"Started dynamic lighting scene '{all_scenes[scene]['name']}' on {', '.join(entity_ids)}",
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
                        f"Applied lighting scene '{all_scenes[scene]['name']}' on {success} lights.",
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
