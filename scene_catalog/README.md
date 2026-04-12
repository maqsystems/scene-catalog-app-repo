# Scene Catalog App

Minimal Home Assistant app (add-on) that provides an ingress page with a small scene catalog.
You pick a scene and target lights, then it calls Home Assistant `light.turn_on` for you.

## Features

- Built-in palette catalog inspired by cinematic Hue-like moods
- Fixed scenes distribute palette colors across selected lights
- Dynamic scenes rotate palette distribution over time across the same lights
- Simple ingress UI with light multi-select

## Install

1. Add the repository URL to Home Assistant app repositories.
2. Install `Scene Catalog App`.
3. Start the app.
4. Open it from the sidebar.

## Notes

- This is intentionally simple for a first working version.
- Next iterations can add dynamic scenes, richer catalog metadata, and persistent favorites.
