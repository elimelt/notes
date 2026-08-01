#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUARTZ_DIR="${QUARTZ_DIR:-$ROOT/.quartz}"
QUARTZ_REPOSITORY="${QUARTZ_REPOSITORY:-https://github.com/jackyzha0/quartz.git}"
QUARTZ_REF="${QUARTZ_REF:-v5}"

usage() {
  cat <<'EOF'
Usage: scripts/quartz.sh <build|serve|sync>

Environment overrides:
  QUARTZ_DIR         Cached Quartz checkout (default: .quartz)
  QUARTZ_REPOSITORY  Quartz Git repository
  QUARTZ_REF         Quartz branch/tag/commit (default: v5)
EOF
}

publish_legacy_docs() {
  if [[ -d "$ROOT/public/static/docs" ]]; then
    rm -rf "$ROOT/public/docs"
    cp -R "$ROOT/public/static/docs" "$ROOT/public/docs"
  fi
}

publish_standalone_routes() {
  if [[ -d "$ROOT/quartz-site/routes" ]]; then
    cp -R "$ROOT/quartz-site/routes/." "$ROOT/public/"
  fi
}

bootstrap() {
  local ref_stamp="$QUARTZ_DIR/.notes-quartz-ref"
  if [[ ! -d "$QUARTZ_DIR/.git" ]] || [[ ! -f "$ref_stamp" ]] || [[ "$(<"$ref_stamp")" != "$QUARTZ_REF" ]]; then
    rm -rf "$QUARTZ_DIR"
    git clone --depth 1 --branch "$QUARTZ_REF" "$QUARTZ_REPOSITORY" "$QUARTZ_DIR"
    printf '%s\n' "$QUARTZ_REF" > "$ref_stamp"
  fi

  if [[ ! -d "$QUARTZ_DIR/node_modules" ]]; then
    npm --prefix "$QUARTZ_DIR" ci
  fi
}

sync_site() {
  rm -rf "$QUARTZ_DIR/content"
  cp -R "$ROOT/content" "$QUARTZ_DIR/content"
  python3 "$ROOT/scripts/prepare_content.py" "$QUARTZ_DIR/content"
  cp "$ROOT/quartz.config.yaml" "$QUARTZ_DIR/quartz.config.yaml"
  if [[ -f "$ROOT/quartz.lock.json" ]]; then
    cp "$ROOT/quartz.lock.json" "$QUARTZ_DIR/quartz.lock.json"
  fi
  cp "$ROOT/quartz-site/custom.scss" "$QUARTZ_DIR/quartz/styles/custom.scss"
  mkdir -p "$QUARTZ_DIR/quartz/static"
  cp -R "$ROOT/quartz-site/static/." "$QUARTZ_DIR/quartz/static/"
  if [[ -d "$ROOT/docs" ]]; then
    rm -rf "$QUARTZ_DIR/quartz/static/docs"
    cp -R "$ROOT/docs" "$QUARTZ_DIR/quartz/static/docs"
  fi
}

enable_style_debug_panel() {
  python3 "$ROOT/scripts/enable_style_debug_panel.py" "$QUARTZ_DIR/quartz.config.yaml"
}

install_plugins() {
  (cd "$QUARTZ_DIR" && npx quartz plugin install --concurrency 2)
  patch_mermaid_defaults
}

sync_plugins() {
  (cd "$QUARTZ_DIR" && npx quartz plugin install --from-config --concurrency 2)
  cp "$QUARTZ_DIR/quartz.lock.json" "$ROOT/quartz.lock.json"
  patch_mermaid_defaults
}

# Mermaid only wraps sequence-diagram note/message text when the client
# config sets sequence.wrap, and the obsidian-flavored-markdown plugin does
# not expose mermaid options. It also renders before webfonts finish loading,
# so box sizes get measured with a fallback font and the real (wider) code
# font overflows them. Inject both fixes into the bundled client script after
# every plugin install (the checkout is disposable).
patch_mermaid_defaults() {
  local ofm_dist="$QUARTZ_DIR/node_modules/@quartz-community/obsidian-flavored-markdown/dist/index.js"
  if [[ ! -f "$ofm_dist" ]]; then
    return
  fi
  if ! grep -q 'sequence:{wrap:!0}' "$ofm_dist"; then
    sed -i.bak 's/initialize({startOnLoad:!1,/initialize({startOnLoad:!1,sequence:{wrap:!0},/' "$ofm_dist"
    rm -f "$ofm_dist.bak"
  fi
  if ! grep -q 'document\.fonts\.ready' "$ofm_dist"; then
    sed -i.bak 's/await t.run({nodes:e})/await document.fonts.ready,await t.run({nodes:e})/' "$ofm_dist"
    rm -f "$ofm_dist.bak"
  fi
  if ! grep -q 'sequence:{wrap:!0}' "$ofm_dist" || ! grep -q 'document\.fonts\.ready' "$ofm_dist"; then
    echo "warning: mermaid default patch did not apply cleanly to $ofm_dist" >&2
  fi
}

prepare_notebooks() {
  python3 "$ROOT/scripts/render_notebooks.py" \
    --cache-dir "$QUARTZ_DIR/.quartz-cache/notebooks"
}

command="${1:-}"
case "$command" in
  build)
    bootstrap
    prepare_notebooks
    sync_site
    install_plugins
    (cd "$QUARTZ_DIR" && npx quartz build --output "$ROOT/public")
    publish_standalone_routes
    python3 "$ROOT/scripts/prepare_graph_index.py" "$ROOT/public/static/contentIndex.json"
    python3 "$ROOT/scripts/validate_graph_index.py" "$ROOT/public/static/contentIndex.json"
    publish_legacy_docs
    ;;
  serve)
    bootstrap
    prepare_notebooks
    sync_site
    enable_style_debug_panel
    install_plugins
    (cd "$QUARTZ_DIR" && npx quartz build --serve --port "${QUARTZ_PORT:-8080}")
    ;;
  sync)
    bootstrap
    prepare_notebooks
    sync_site
    sync_plugins
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
