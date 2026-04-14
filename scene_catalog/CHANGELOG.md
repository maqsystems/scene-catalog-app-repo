# Changelog

## 0.3.0

- Rename the visible app and integration labels to `Lighting Scene Studio`
- Rename service labels to `Apply Lighting Scene` and related dynamic variants
- Add a first custom scene builder directly in the app UI
- Store custom scenes in the shared Home Assistant config folder so the integration can reuse them

## 0.2.1

- Fix Python indentation in scene apply loop causing startup crash (`IndentationError`)

## 0.2.0

- Add palette-based scenes that distribute different colors across selected lights
- Add dynamic scenes that rotate palette distribution over time
- Add Start Dynamic / Stop Dynamic controls in the ingress UI
- Add per-light apply feedback (partial success/error details)

## 0.1.5

- Auto-discover `light.*` entities from Home Assistant API
- Replace free text targets with multi-select light picker when discovery works
- Keep text input fallback if discovery fails

## 0.1.4

- Fix ingress form routing (`/apply`) that caused 404 when applying a scene
- Improve displayed Home Assistant API error text

## 0.1.3

- Rotate addon slug to `scene_catalog_v2` to bypass stale Supervisor AppArmor unload state

## 0.1.2

- Remove apparmor.txt entirely to avoid Supervisor profile load failure on install

## 0.1.1

- Disable AppArmor profile for initial install reliability

## 0.1.0

- Initial minimal app release
- Ingress UI with scene selection
- Scene apply to selected lights using Home Assistant API
