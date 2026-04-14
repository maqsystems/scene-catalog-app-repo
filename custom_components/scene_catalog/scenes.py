from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .const import DOMAIN

BUILTIN_SCENES = {
    # Fixed scenes
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

    # Dynamic scenes
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


def _custom_scene_file(hass) -> Path:
    scene_dir = Path(hass.config.path(DOMAIN))
    scene_dir.mkdir(parents=True, exist_ok=True)
    return scene_dir / "custom_scenes.json"


def load_custom_scenes(hass) -> dict:
    path = _custom_scene_file(hass)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def save_custom_scene(hass, scene_key: str, scene_data: dict) -> None:
    scenes = load_custom_scenes(hass)
    scenes[scene_key] = scene_data
    _custom_scene_file(hass).write_text(json.dumps(scenes, indent=2), encoding="utf-8")


def delete_custom_scene(hass, scene_key: str) -> bool:
    scenes = load_custom_scenes(hass)
    if scene_key not in scenes:
        return False
    del scenes[scene_key]
    _custom_scene_file(hass).write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    return True


def get_all_scenes(hass=None) -> dict:
    scenes = deepcopy(BUILTIN_SCENES)
    if hass is not None:
        scenes.update(load_custom_scenes(hass))
    return scenes


def get_scene(hass, scene_key: str) -> dict:
    return get_all_scenes(hass)[scene_key]


def get_scene_keys_by_kind(hass=None, kind: str = "fixed") -> list[str]:
    return [
        key for key, value in get_all_scenes(hass).items() if value.get("kind", "fixed") == kind
    ]


def get_fixed_scene_keys(hass=None) -> list[str]:
    return get_scene_keys_by_kind(hass, "fixed")


def get_dynamic_scene_keys(hass=None) -> list[str]:
    return get_scene_keys_by_kind(hass, "dynamic")
