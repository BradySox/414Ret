#!/bin/bash
# SessionStart hook: surface the 414th in-game-pass checklist status board so
# Claude can present it to the user at the start of every session. Read-only;
# prints to stdout, which Claude Code adds to the session context.
set -euo pipefail

md="${CLAUDE_PROJECT_DIR:-.}/docs/dev/414th-ingame-pass-checklist.md"
[ -f "$md" ] || exit 0   # checklist absent (e.g. stale checkout) — nothing to do

# Status markers (☑ ☐ ◐ ✗) live in section/row HEADING lines (## / ###). Scoping
# to headings deliberately excludes the legend table (| ☐ ... |) and prose notes,
# which also contain the symbols but are not tracked rows.
headings="$(grep -E '^#{2,3} ' "$md" || true)"
count() { printf '%s\n' "$headings" | grep -cF "$1" || true; }

echo "=== 414th in-game-pass checklist ==="
echo "verified $(count '☑ VERIFIED') | untested $(count '☐ UNTESTED') | partial $(count '◐ PARTIAL') | regressed $(count '✗ REGRESSED')"
echo

outstanding="$(printf '%s\n' "$headings" \
  | grep -E '☐ UNTESTED|◐ PARTIAL|✗ REGRESSED' \
  | sed -E 's/^#+ +//' || true)"
if [ -n "$outstanding" ]; then
  echo "Outstanding (needs an in-game pass):"
  printf '%s\n' "$outstanding"
else
  echo "All tracked rows verified — nothing outstanding."
fi
echo
echo "Source: docs/dev/414th-ingame-pass-checklist.md"
echo "[Claude: present this board to the user near the top of your first reply.]"
