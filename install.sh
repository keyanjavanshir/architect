#!/usr/bin/env sh
# Install the agent-architect skill.
#   ./install.sh            user-level: ~/.agents/skills (Codex, Copilot CLI, Gemini CLI,
#                           Cursor, OpenCode) + link in ~/.claude/skills (Claude Code)
#   ./install.sh --project  into the current directory's .agents/skills + .claude/skills
#   ./install.sh --copy     copy instead of symlinking into .claude/skills
set -eu

SRC="$(cd "$(dirname "$0")" && pwd)/skills/agent-architect"
SCOPE="user"
COPY=0
for arg in "$@"; do
  case "$arg" in
    --project) SCOPE="project" ;;
    --copy) COPY=1 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$SCOPE" = "project" ]; then BASE="$(pwd)"; else BASE="$HOME"; fi
AGENTS_DIR="$BASE/.agents/skills/agent-architect"
CLAUDE_DIR="$BASE/.claude/skills/agent-architect"

mkdir -p "$(dirname "$AGENTS_DIR")" "$(dirname "$CLAUDE_DIR")"
rm -rf "$AGENTS_DIR"
cp -R "$SRC" "$AGENTS_DIR"
find "$AGENTS_DIR" -name __pycache__ -prune -exec rm -rf {} +
echo "installed $AGENTS_DIR"

rm -rf "$CLAUDE_DIR"
if [ "$COPY" = "1" ] || ! ln -s "$AGENTS_DIR" "$CLAUDE_DIR" 2>/dev/null; then
  cp -R "$SRC" "$CLAUDE_DIR"
  echo "copied   $CLAUDE_DIR"
else
  echo "linked   $CLAUDE_DIR -> $AGENTS_DIR"
fi

if ! python3 -c "import yaml" 2>/dev/null; then
  echo "note: the scripts need PyYAML: pip install pyyaml"
fi
echo "Restart your harness (or run /skills reload) and ask for /agent-architect."
