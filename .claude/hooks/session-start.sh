#!/bin/bash
# SessionStart hook: surface the 414th in-game-pass checklist status board so
# Claude can present it to the user at the start of every session. Read-only;
# prints to stdout, which Claude Code adds to the session context.
set -euo pipefail

md="${CLAUDE_PROJECT_DIR:-.}/docs/dev/414th-ingame-pass-checklist.md"
[ -f "$md" ] || exit 0   # checklist absent (e.g. stale checkout) — nothing to do

# Status markers (☑ ☐ ◐ ✗ ⊘ ✖) live in section/row HEADING lines (## / ###).
# Scoping to headings deliberately excludes the legend table (| ☐ ... |) and
# prose notes, which also contain the symbols but are not tracked rows.
headings="$(grep -E '^#{2,3} ' "$md" || true)"

# A row's status is the FIRST marker on its heading line -- never any later one.
# Matching the whole line (the old behaviour) re-admitted rows whose PROSE
# quotes a marker, and the checklist's own conventions quote them constantly:
# every re-verified row carries "(was ☐ UNTESTED, built ...)" and the shelved
# B9 says "Re-open as ☐ UNTESTED if the feature is ever resumed". The effect was
# that VERIFIED and RETIRED rows were listed as outstanding AND double-counted
# into the untested total. `index()` is byte-based, so the UTF-8 markers match
# literally and no assumption is made about the " · " separators, which prose
# also uses.
statuses="$(printf '%s\n' "$headings" | awk '
  function first_status(s,   i, at, best, best_name) {
    best = 0; best_name = ""
    for (i = 1; i <= n_markers; i++) {
      at = index(s, marker[i])
      if (at > 0 && (best == 0 || at < best)) { best = at; best_name = marker[i] }
    }
    return best_name
  }
  BEGIN {
    n_markers = split("☑ VERIFIED|☐ UNTESTED|◐ PARTIAL|✗ REGRESSED|⊘ RETIRED|✖ REMOVED",
                      marker, "|")
  }
  { st = first_status($0); if (st != "") print st }
')"
count() { printf '%s\n' "$statuses" | grep -cFx "$1" || true; }

echo "=== 414th in-game-pass checklist ==="
echo "verified $(count '☑ VERIFIED') | untested $(count '☐ UNTESTED') | partial $(count '◐ PARTIAL') | regressed $(count '✗ REGRESSED') | closed $(( $(count '⊘ RETIRED') + $(count '✖ REMOVED') ))"
echo

outstanding="$(printf '%s\n' "$headings" | awk '
  function first_status(s,   i, at, best, best_name) {
    best = 0; best_name = ""
    for (i = 1; i <= n_markers; i++) {
      at = index(s, marker[i])
      if (at > 0 && (best == 0 || at < best)) { best = at; best_name = marker[i] }
    }
    return best_name
  }
  BEGIN {
    n_markers = split("☑ VERIFIED|☐ UNTESTED|◐ PARTIAL|✗ REGRESSED|⊘ RETIRED|✖ REMOVED",
                      marker, "|")
    n_open = split("☐ UNTESTED|◐ PARTIAL|✗ REGRESSED", open, "|")
  }
  {
    st = first_status($0)
    for (i = 1; i <= n_open; i++) {
      if (st == open[i]) { line = $0; sub(/^#+ +/, "", line); print line; break }
    }
  }
' || true)"
if [ -n "$outstanding" ]; then
  echo "Outstanding (needs an in-game pass):"
  printf '%s\n' "$outstanding"
else
  echo "All tracked rows verified — nothing outstanding."
fi
echo
echo "Source: docs/dev/414th-ingame-pass-checklist.md"

# --- WATCH list -------------------------------------------------------------
# The standing daily-fly list: rows that close from ORDINARY flying if someone
# is looking. Parsed from the file rather than hardcoded so rotating an item is
# a one-line edit to WATCH.md and never a hook change. Item headings are the
# only `### ` lines in that file (the parking lot is a table, its sections are
# `## `), so this stays correct as the list churns.
watch="${CLAUDE_PROJECT_DIR:-.}/docs/dev/flycards/WATCH.md"
if [ -f "$watch" ]; then
  items="$(grep -E '^### ' "$watch" | sed -e 's/^### //' -e 's/`//g' || true)"
  if [ -n "$items" ]; then
    echo
    echo "=== WATCH — look for these on the next fly ==="
    printf '%s\n' "$items" | sed 's/^/  /'
    echo "Source: docs/dev/flycards/WATCH.md (pass/fail detail per item)"
  fi
fi

echo "[Claude: present this board to the user near the top of your first reply."
echo " Re-surface the WATCH list whenever the user is about to fly, generate a"
echo " turn, or otherwise test — link docs/dev/flycards/WATCH.md.]"
