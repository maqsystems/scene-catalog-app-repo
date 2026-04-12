# Scene Catalog Repository

This repository contains two deliverables:

1. `scene_catalog/` -> Home Assistant app (add-on style) with an ingress UI.
2. `custom_components/scene_catalog/` -> Home Assistant custom integration exposing automation-friendly services.

## Install the integration (recommended for automations)

1. Add this repository in HACS as a custom repository of type `integration`.
2. Install `Scene Catalog Services`.
3. Restart Home Assistant.
4. Add integration `Scene Catalog Services` in Devices & Services.

Available services in automations:

- `scene_catalog.apply_scene`
- `scene_catalog.start_dynamic_scene`
- `scene_catalog.stop_dynamic_scene`
- `scene_catalog.stop_all_dynamic_scenes`
- `scene_catalog.list_scenes`

## Install the app (optional UI)

If you also want the ingress app UI, add this repository in Home Assistant app repositories and install `Scene Catalog App`.
