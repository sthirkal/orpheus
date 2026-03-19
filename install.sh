#!/usr/bin/env bash
# ── orpheus installer ──────────────────────────────────────────────
# sets up the `orpheus` command so you can run it from anywhere

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORPHEUS_PY="$SCRIPT_DIR/orpheus.py"
INSTALL_DIR="$HOME/.local/bin"
WRAPPER="$INSTALL_DIR/orpheus"

# ── check python ───────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "✗ python3 not found. please install it first."
  exit 1
fi

# ── make install dir ───────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"

# ── write wrapper script ───────────────────────────────────────────
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
exec python3 "$ORPHEUS_PY" "\$@"
EOF
chmod +x "$WRAPPER"

echo "✓ installed orpheus → $WRAPPER"

# ── check if ~/.local/bin is in PATH ──────────────────────────────
SHELL_NAME="$(basename "$SHELL")"
RC_FILE=""

case "$SHELL_NAME" in
  bash) RC_FILE="$HOME/.bashrc" ;;
  zsh)  RC_FILE="$HOME/.zshrc"  ;;
  fish) RC_FILE="$HOME/.config/fish/config.fish" ;;
  *)    RC_FILE="$HOME/.profile" ;;
esac

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
  echo ""
  echo "  ~/.local/bin is not in your PATH yet."
  echo "  adding it to $RC_FILE ..."
  echo ""

  if [[ "$SHELL_NAME" == "fish" ]]; then
    echo "fish_add_path \$HOME/.local/bin" >> "$RC_FILE"
  else
    echo "" >> "$RC_FILE"
    echo '# orpheus' >> "$RC_FILE"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
  fi

  echo "✓ added PATH entry to $RC_FILE"
  echo ""
  echo "  run this to apply it now:"
  echo ""
  echo "    source $RC_FILE"
  echo ""
  echo "  then just type:  orpheus"
  echo "              or:  orpheus myfile.md"
else
  echo ""
  echo "  you're all set. just type:"
  echo ""
  echo "    orpheus"
  echo "    orpheus myfile.md"
  echo ""
fi
