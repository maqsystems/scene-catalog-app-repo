from __future__ import annotations

import asyncio
import math
import random
import uuid
from dataclasses import dataclass

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import area_registry, device_registry, entity_registry

from .const import (
    ATTR_BRIGHTNESS,
    ATTR_DYNAMIC_ID,
    ATTR_INTERVAL,
    ATTR_SCENE,
    ATTR_TARGET,
    ATTR_TRANSITION,
    DOMAIN,
    SERVICE_APPLY_SCENE,
    SERVICE_LIST_SCENES,
    SERVICE_START_DYNAMIC_SCENE,
    SERVICE_STOP_ALL_DYNAMIC_SCENES,
    SERVICE_STOP_DYNAMIC_SCENE,
)
from .scenes import get_all_scenes, get_dynamic_scene_keys, get_fixed_scene_keys, get_scene

APPLY_SCENE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCENE): cv.string,
        vol.Required(ATTR_TARGET): vol.Any(dict),
        vol.Optional(ATTR_TRANSITION): vol.Coerce(int),
        vol.Optional(ATTR_BRIGHTNESS): vol.Coerce(int),
    }
)

START_DYNAMIC_SCENE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_SCENE): cv.string,
        vol.Required(ATTR_TARGET): vol.Any(dict),
        vol.Optional(ATTR_INTERVAL): vol.Coerce(int),
        vol.Optional(ATTR_TRANSITION): vol.Coerce(int),
        vol.Optional(ATTR_BRIGHTNESS): vol.Coerce(int),
    }
)

STOP_DYNAMIC_SCENE_SCHEMA = vol.Schema({vol.Required(ATTR_DYNAMIC_ID): cv.string})


@dataclass
class DynamicScene:
    id: str
    task: asyncio.Task | None
    scene_key: str
    entity_ids: list[str]
    interval: int
    transition: int | None
    brightness: int | None
    frame: int = 0


class DynamicSceneManager:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.scenes: dict[str, DynamicScene] = {}

    async def start(
        self,
        scene_key: str,
        entity_ids: list[str],
        interval: int,
        transition: int | None,
        brightness: int | None,
    ) -> str:
        if scene_key not in get_dynamic_scene_keys(self.hass):
            raise vol.Invalid(f"Scene '{scene_key}' is not dynamic")

        dynamic_id = str(uuid.uuid4())
        scene = DynamicScene(
            id=dynamic_id,
            task=None,
            scene_key=scene_key,
            entity_ids=list(entity_ids),
            interval=max(1, interval),
            transition=transition,
            brightness=brightness,
            frame=0,
        )
        self.scenes[dynamic_id] = scene

        async def _runner() -> None:
            while True:
                current = self.scenes.get(dynamic_id)
                if current is None:
                    return

                current_entities = list(current.entity_ids)
                if not current_entities:
                    self.stop(dynamic_id)
                    return

                await apply_scene_to_entities(
                    self.hass,
                    current.scene_key,
                    current_entities,
                    dynamic=True,
                    frame=current.frame,
                    transition_override=current.transition,
                    brightness_override=current.brightness,
                )
                current.frame += 1
                await asyncio.sleep(max(1, current.interval))

        task = self.hass.async_create_task(_runner())
        scene.task = task
        return dynamic_id

    def stop(self, dynamic_id: str) -> bool:
        scene = self.scenes.pop(dynamic_id, None)
        if not scene:
            return False
        if scene.task is not None:
            scene.task.cancel()
        return True

    def remove_entities(self, entity_ids: list[str]) -> dict:
        removed_set = set(entity_ids)
        touched_ids = []
        stopped_ids = []

        for dynamic_id, scene in list(self.scenes.items()):
            before = set(scene.entity_ids)
            remaining = [entity_id for entity_id in scene.entity_ids if entity_id not in removed_set]
            if len(remaining) != len(scene.entity_ids):
                touched_ids.append(dynamic_id)
                scene.entity_ids = remaining

            if not scene.entity_ids and before:
                self.stop(dynamic_id)
                stopped_ids.append(dynamic_id)

        return {
            "touched_dynamic_ids": touched_ids,
            "stopped_dynamic_ids": stopped_ids,
        }

    def stop_all(self) -> int:
        ids = list(self.scenes.keys())
        for dynamic_id in ids:
            self.stop(dynamic_id)
        return len(ids)

    def as_dict(self) -> dict:
        return {
            "running": [
                {
                    "id": s.id,
                    "scene": s.scene_key,
                    "entities": s.entity_ids,
                }
                for s in self.scenes.values()
            ]
        }


def _ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def _get_config_entry(hass: HomeAssistant, entity_id: str):
    entity_reg = entity_registry.async_get(hass)
    entity_reg_entry = entity_reg.async_get(entity_id)
    if not entity_reg_entry:
        return None
    return hass.config_entries.async_get_entry(entity_reg_entry.config_entry_id)


def _resolve_entity_ids(hass: HomeAssistant, entity_id: str, depth: int = 0) -> list[str]:
    if depth > 4:
        return []

    if not entity_id.startswith(("light.", "group.")):
        return []

    state = hass.states.get(entity_id)
    if not state:
        return []

    nested = state.attributes.get("entity_id", [])
    if not nested:
        return [entity_id] if entity_id.startswith("light.") else []

    conf_entry = _get_config_entry(hass, entity_id)
    if conf_entry is not None and conf_entry.domain != "group":
        return [entity_id] if entity_id.startswith("light.") else []

    resolved: list[str] = []
    for nested_entity in nested:
        resolved.extend(_resolve_entity_ids(hass, nested_entity, depth + 1))
    return resolved


def resolve_targets(hass: HomeAssistant, target: dict) -> list[str]:
    entity_reg = entity_registry.async_get(hass)
    device_reg = device_registry.async_get(hass)
    area_reg = area_registry.async_get(hass)

    entity_ids_to_process = set(_ensure_list(target.get("entity_id")))
    device_ids_to_process = set(_ensure_list(target.get("device_id")))
    area_ids_to_process = set(_ensure_list(target.get("area_id")))
    floor_ids = _ensure_list(target.get("floor_id"))
    label_ids = _ensure_list(target.get("label_id"))

    for label_id in label_ids:
        for entry in entity_registry.async_entries_for_label(entity_reg, label_id):
            entity_ids_to_process.add(entry.entity_id)
        for entry in device_registry.async_entries_for_label(device_reg, label_id):
            device_ids_to_process.add(entry.id)
        for entry in area_registry.async_entries_for_label(area_reg, label_id):
            area_ids_to_process.add(entry.id)

    for floor_id in floor_ids:
        for entry in area_registry.async_entries_for_floor(area_reg, floor_id):
            area_ids_to_process.add(entry.id)

    for area_id in area_ids_to_process:
        for entry in entity_registry.async_entries_for_area(entity_reg, area_id):
            entity_ids_to_process.add(entry.entity_id)

        for device in device_registry.async_entries_for_area(device_reg, area_id):
            for entry in entity_registry.async_entries_for_device(entity_reg, device.id):
                if entry.area_id is None or entry.area_id == area_id:
                    entity_ids_to_process.add(entry.entity_id)

    for device_id in device_ids_to_process:
        for entry in entity_registry.async_entries_for_device(entity_reg, device_id):
            entity_ids_to_process.add(entry.entity_id)

    resolved: list[str] = []
    for entity_id in entity_ids_to_process:
        resolved.extend(_resolve_entity_ids(hass, entity_id))

    deduped = list(dict.fromkeys(resolved))
    return deduped


def _scene_palette_color(palette: list[list[float]], index: int, total: int, phase: float = 0.0) -> list[float]:
    if not palette:
        return [0.35, 0.35]

    if total <= 1:
        return palette[int(math.floor(phase)) % len(palette)]

    spread = (index / total) * len(palette)
    palette_index = int(math.floor(spread + phase)) % len(palette)
    return palette[palette_index]


def _scene_kind(hass: HomeAssistant, scene_key: str) -> str:
    scenes = get_all_scenes(hass)
    if scene_key not in scenes:
        raise vol.Invalid(f"Unknown scene '{scene_key}'")
    return scenes[scene_key].get("kind", "fixed")


def _validate_scene_kind(hass: HomeAssistant, scene_key: str, expected_kind: str) -> None:
    kind = _scene_kind(hass, scene_key)
    if kind != expected_kind:
        raise vol.Invalid(
            f"Scene '{scene_key}' is '{kind}', expected '{expected_kind}'"
        )


async def apply_scene_to_entities(
    hass: HomeAssistant,
    scene_key: str,
    entity_ids: list[str],
    dynamic: bool = False,
    frame: int = 0,
    transition_override: int | None = None,
    brightness_override: int | None = None,
) -> dict:
    scenes = get_all_scenes(hass)
    if scene_key not in scenes:
        raise vol.Invalid(f"Unknown scene '{scene_key}'")

    scene = get_scene(hass, scene_key)
    palette = scene.get("palette", [])
    brightness = int(brightness_override if brightness_override is not None else scene.get("brightness", 180))
    transition = float(transition_override if transition_override is not None else scene.get("transition", 1))
    phase = float(scene.get("dynamic_step", 0.6)) * frame if dynamic else 0.0
    dynamic_transition_range = scene.get("dynamic_transition_range", [transition, transition])
    stagger_max = float(scene.get("dynamic_stagger_max", 0.0)) if dynamic else 0.0

    tasks = []

    async def _apply_single(payload: dict, delay: float) -> None:
        if delay > 0:
            await asyncio.sleep(delay)
        await hass.services.async_call("light", "turn_on", payload, blocking=False)

    for idx, entity_id in enumerate(entity_ids):
        color = _scene_palette_color(palette, idx, len(entity_ids), phase=phase)

        current_transition = transition
        if dynamic and isinstance(dynamic_transition_range, list) and len(dynamic_transition_range) == 2:
            low = float(dynamic_transition_range[0])
            high = float(dynamic_transition_range[1])
            if low > high:
                low, high = high, low
            current_transition = round(random.uniform(low, high), 2)

        delay = round(random.uniform(0, stagger_max), 3) if stagger_max > 0 else 0.0

        payload = {
            "entity_id": entity_id,
            "xy_color": color,
            "brightness": brightness,
            "transition": current_transition,
        }
        tasks.append(_apply_single(payload, delay))

    await asyncio.gather(*tasks)
    return {
        "scene": scene_key,
        "dynamic": dynamic,
        "applied_count": len(entity_ids),
        "entity_ids": entity_ids,
    }


async def _async_setup_services(hass: HomeAssistant) -> bool:
    hass.data.setdefault(DOMAIN, {})
    manager = hass.data[DOMAIN].setdefault("dynamic_manager", DynamicSceneManager(hass))

    if hass.data[DOMAIN].get("services_registered"):
        return True

    async def _apply_scene(call: ServiceCall):
        scene_key = call.data[ATTR_SCENE]
        _validate_scene_kind(hass, scene_key, "fixed")

        target = call.data[ATTR_TARGET]
        transition = call.data.get(ATTR_TRANSITION)
        brightness = call.data.get(ATTR_BRIGHTNESS)
        entity_ids = resolve_targets(hass, target)
        if not entity_ids:
            raise vol.Invalid("No light entities resolved from target")

        dynamic_cleanup = manager.remove_entities(entity_ids)

        result = await apply_scene_to_entities(
            hass,
            scene_key,
            entity_ids,
            dynamic=False,
            transition_override=transition,
            brightness_override=brightness,
        )
        result["dynamic_cleanup"] = dynamic_cleanup
        return result

    async def _start_dynamic_scene(call: ServiceCall):
        scene_key = call.data[ATTR_SCENE]
        _validate_scene_kind(hass, scene_key, "dynamic")

        target = call.data[ATTR_TARGET]
        interval = max(1, int(call.data.get(ATTR_INTERVAL, get_scene(hass, scene_key).get("dynamic_interval", 8))))
        transition = call.data.get(ATTR_TRANSITION)
        brightness = call.data.get(ATTR_BRIGHTNESS)
        entity_ids = resolve_targets(hass, target)
        if not entity_ids:
            raise vol.Invalid("No light entities resolved from target")

        dynamic_id = await manager.start(scene_key, entity_ids, interval, transition, brightness)
        return {
            "id": dynamic_id,
            "scene": scene_key,
            "entity_ids": entity_ids,
            "interval": interval,
        }

    async def _stop_dynamic_scene(call: ServiceCall):
        dynamic_id = call.data[ATTR_DYNAMIC_ID]
        return {"stopped": manager.stop(dynamic_id), "id": dynamic_id}

    async def _stop_all_dynamic_scenes(call: ServiceCall):
        stopped_count = manager.stop_all()
        return {"stopped_count": stopped_count}

    async def _list_scenes(call: ServiceCall):
        all_scenes = get_all_scenes(hass)

        def scene_payload(keys: list[str]) -> list[dict]:
            payload = []
            for key in keys:
                value = all_scenes[key]
                payload.append(
                    {
                        "key": key,
                        "name": value.get("name", key),
                        "kind": value.get("kind", "fixed"),
                        "dynamic_interval": value.get("dynamic_interval"),
                        "dynamic_transition_range": value.get("dynamic_transition_range"),
                        "dynamic_stagger_max": value.get("dynamic_stagger_max"),
                        "transition": value.get("transition", 1),
                        "brightness": value.get("brightness", 180),
                    }
                )
            return payload

        return {
            "fixed_scenes": scene_payload(get_fixed_scene_keys(hass)),
            "dynamic_scenes": scene_payload(get_dynamic_scene_keys(hass)),
            "dynamic": manager.as_dict(),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_APPLY_SCENE,
        _apply_scene,
        schema=APPLY_SCENE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_DYNAMIC_SCENE,
        _start_dynamic_scene,
        schema=START_DYNAMIC_SCENE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_DYNAMIC_SCENE,
        _stop_dynamic_scene,
        schema=STOP_DYNAMIC_SCENE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ALL_DYNAMIC_SCENES,
        _stop_all_dynamic_scenes,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_SCENES,
        _list_scenes,
        supports_response=SupportsResponse.ONLY,
    )

    hass.data[DOMAIN]["services_registered"] = True
    return True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    # Optional YAML fallback: scene_catalog: {}
    if DOMAIN in config:
        await _async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await _async_setup_services(hass)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        return True

    manager: DynamicSceneManager | None = domain_data.get("dynamic_manager")
    if manager is not None:
        manager.stop_all()

    if hass.services.has_service(DOMAIN, SERVICE_APPLY_SCENE):
        hass.services.async_remove(DOMAIN, SERVICE_APPLY_SCENE)
    if hass.services.has_service(DOMAIN, SERVICE_START_DYNAMIC_SCENE):
        hass.services.async_remove(DOMAIN, SERVICE_START_DYNAMIC_SCENE)
    if hass.services.has_service(DOMAIN, SERVICE_STOP_DYNAMIC_SCENE):
        hass.services.async_remove(DOMAIN, SERVICE_STOP_DYNAMIC_SCENE)
    if hass.services.has_service(DOMAIN, SERVICE_STOP_ALL_DYNAMIC_SCENES):
        hass.services.async_remove(DOMAIN, SERVICE_STOP_ALL_DYNAMIC_SCENES)
    if hass.services.has_service(DOMAIN, SERVICE_LIST_SCENES):
        hass.services.async_remove(DOMAIN, SERVICE_LIST_SCENES)

    hass.data.pop(DOMAIN, None)
    return True
