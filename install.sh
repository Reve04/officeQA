#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${ARENA_INSTALL_DIR:-$HOME/.arena}"

echo "Installing arena-cli to $INSTALL_DIR ..."

# Check for uv
if ! command -v uv &>/dev/null; then
  echo "Error: uv is required. Install it: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

# Create install directory and venv
mkdir -p "$INSTALL_DIR"
uv venv "$INSTALL_DIR/venv" --python ">=3.13" --quiet

# Install all wheels (order matters: core-data, core, then sdk+harbor, then cli)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
uv pip install --python "$INSTALL_DIR/venv/bin/python" \
  "$SCRIPT_DIR"/arena_core_data-*.whl \
  "$SCRIPT_DIR"/arena_core-*.whl \
  "$SCRIPT_DIR"/harbor-*.whl \
  "$SCRIPT_DIR"/arena_sdk-*.whl \
  "$SCRIPT_DIR"/cli_commons-*.whl \
  "$SCRIPT_DIR"/arena_cli-*.whl \
  --quiet

# Copy environment config (baked in at build time)
if [ -f "$SCRIPT_DIR/env.json" ]; then
  cp "$SCRIPT_DIR/env.json" "$INSTALL_DIR/env.json"
fi

# Create stable wrapper that calls venv python directly
# (immune to stale shebangs after auto-update venv swaps)
mkdir -p "$INSTALL_DIR/bin"
printf '#!/usr/bin/env bash\nexec "%s/venv/bin/python" -m arena_cli.main "$@"\n' "$INSTALL_DIR" > "$INSTALL_DIR/bin/arena"
chmod +x "$INSTALL_DIR/bin/arena"

echo ""
echo "arena-cli installed successfully!"
echo ""
echo "Add to your PATH:"
echo "  export PATH=\"$INSTALL_DIR/bin:\$PATH\""
echo ""
echo "Then run:"
echo "  arena auth login"
echo "  arena doctor"
