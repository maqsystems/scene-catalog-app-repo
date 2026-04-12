ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

RUN apk add --no-cache python3

COPY rootfs /

RUN chmod a+rx /etc/services.d/scene_catalog/run

LABEL \
  org.opencontainers.image.title="Home Assistant App: Scene Catalog" \
  org.opencontainers.image.description="Apply simple curated light scenes from a small catalog" \
  org.opencontainers.image.source="https://github.com/maqsystems/scene-catalog-app-repo" \
  org.opencontainers.image.licenses="MIT"
