# Lighting Scene Studio App

Minimal Home Assistant app (add-on) that provides an ingress page with a lighting-scene catalog and a first custom scene builder.
You pick or create a lighting scene, target lights, then apply it directly from the app.

## Features

- Built-in palette catalog inspired by cinematic Hue-like moods
- Fixed lighting scenes distribute palette colors across selected lights
- Dynamic lighting scenes rotate palette distribution over time across the same lights
- Simple ingress UI with light multi-select
- First custom scene builder for creating and updating your own scenes

## Install

1. Add the repository URL to Home Assistant app repositories.
2. Install `Scene Catalog App`.
3. Start the app.
4. Open it from the sidebar.

## Notes

- This is intentionally simple for a first working version.
- Next iterations can add dynamic scenes, richer catalog metadata, and persistent favorites.
