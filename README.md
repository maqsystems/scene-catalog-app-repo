# Scene Catalog Repository

This repository contains two deliverables:

1. `scene_catalog/` -> Home Assistant app (add-on style) with an ingress UI.
2. `custom_components/scene_catalog/` -> Home Assistant custom integration exposing automation-friendly services.

## Install the integration (recommended for automations)

1. Add this repository in HACS as a custom repository of type `integration`.
2. Install `Scene Catalog Services`.
3. Restart Home Assistant.
4. Add integration `Scene Catalog Services` in Devices & Services.

Important:
If you install only the app (`scene_catalog/`) from Supervisor, Home Assistant services are not automatically registered.
Services are provided by the integration under `custom_components/scene_catalog`.

If the integration does not appear in the UI search, use this fallback once in `configuration.yaml`:

```yaml
scene_catalog: {}
```

Then restart Home Assistant. Services under domain `scene_catalog` will be loaded.

Available services in automations:

- `scene_catalog.apply_scene`
- `scene_catalog.start_dynamic_scene`
- `scene_catalog.stop_dynamic_scene`
- `scene_catalog.stop_all_dynamic_scenes`
- `scene_catalog.list_scenes`

Service behavior notes:

- `apply_scene` accepts fixed scenes only.
- `start_dynamic_scene` accepts dynamic scenes only.
- If `apply_scene` targets entities currently driven by dynamic scenes, those entities are removed from the dynamic runners.
- Dynamic scenes support per-lamp randomized transition duration and per-frame stagger to avoid synchronized changes.

## Install the app (optional UI)

If you also want the ingress app UI, add this repository in Home Assistant app repositories and install `Scene Catalog App`.
