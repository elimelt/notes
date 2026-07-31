#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUARTZ_DIR="${QUARTZ_DIR:-$ROOT/.quartz}"
QUARTZ_REPOSITORY="${QUARTZ_REPOSITORY:-https://github.com/jackyzha0/quartz.git}"
QUARTZ_REF="${QUARTZ_REF:-v4}"

usage() {
  cat <<'EOF'
Usage: scripts/quartz.sh <build|serve|sync>

Environment overrides:
  QUARTZ_DIR         Cached Quartz checkout (default: .quartz)
  QUARTZ_REPOSITORY  Quartz Git repository
  QUARTZ_REF         Quartz branch/tag/commit (default: v4)
EOF
}

publish_legacy_docs() {
  if [[ -d "$ROOT/public/static/docs" ]]; then
    rm -rf "$ROOT/public/docs"
    cp -R "$ROOT/public/static/docs" "$ROOT/public/docs"
  fi
}

bootstrap() {
  if [[ ! -d "$QUARTZ_DIR/.git" ]]; then
    rm -rf "$QUARTZ_DIR"
    git clone --depth 1 --branch "$QUARTZ_REF" "$QUARTZ_REPOSITORY" "$QUARTZ_DIR"
  fi

  if [[ ! -d "$QUARTZ_DIR/node_modules" ]]; then
    npm --prefix "$QUARTZ_DIR" ci
  fi
}

sync_site() {
  rm -rf "$QUARTZ_DIR/content"
  ln -s "$ROOT/content" "$QUARTZ_DIR/content"
  cp "$ROOT/quartz.config.ts" "$QUARTZ_DIR/quartz.config.ts"
  cp "$ROOT/quartz.layout.ts" "$QUARTZ_DIR/quartz.layout.ts"
  cp "$ROOT/quartz.plugins.ts" "$QUARTZ_DIR/quartz.plugins.ts"
  cp "$ROOT/quartz-site/custom.scss" "$QUARTZ_DIR/quartz/styles/custom.scss"
  mkdir -p "$QUARTZ_DIR/quartz/static"
  cp -R "$ROOT/quartz-site/static/." "$QUARTZ_DIR/quartz/static/"
  if [[ -d "$ROOT/docs" ]]; then
    rm -rf "$QUARTZ_DIR/quartz/static/docs"
    cp -R "$ROOT/docs" "$QUARTZ_DIR/quartz/static/docs"
  fi

  if [[ -f "$ROOT/quartz-site/overrides/graph.inline.ts" ]]; then
    cp "$ROOT/quartz-site/overrides/graph.inline.ts" \
      "$QUARTZ_DIR/quartz/components/scripts/graph.inline.ts"
  fi
}

command="${1:-}"
case "$command" in
  build)
    bootstrap
    sync_site
    (cd "$QUARTZ_DIR" && npx quartz build --output "$ROOT/public")
    publish_legacy_docs
    ;;
  serve)
    bootstrap
    sync_site
    (cd "$QUARTZ_DIR" && npx quartz build --serve)
    ;;
  sync)
    bootstrap
    sync_site
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
