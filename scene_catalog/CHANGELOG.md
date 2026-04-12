# Changelog

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
