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
#
# Each item prints as TWO lines: the heading (what to look for) and its
# `**Try:**` paragraph (how to make it happen). Printing the heading alone was
# not enough -- 2026-08-06 an item came back unanswered purely because its
# heading named two row IDs and no observable, and the pass/fail detail that
# would have explained it sits in the body this hook never printed. The Try
# paragraph may wrap across source lines; it is joined back into one line and
# ends at the first blank line. An item with no Try line still prints its
# heading, so a half-written item degrades instead of vanishing.
# Shared by both cards (WATCH + LOCAL) so their formats can never drift apart.
card_items() {
  awk '
    function flush(   t) {
      if (heading == "") return
      print "  " heading
      if (try_text != "") {
        t = try_text
        gsub(/^ +| +$/, "", t)
        print "      Try: " t
      }
      heading = ""; try_text = ""; in_try = 0
    }
    /^### / {
      flush()
      heading = substr($0, 5)
      gsub(/`|\*\*/, "", heading)
      next
    }
    heading == "" { next }
    in_try && /^[[:space:]]*$/ { in_try = 0; next }
    /^\*\*Try:\*\*/ {
      in_try = 1
      try_text = substr($0, 10)
      gsub(/`|\*\*/, "", try_text)
      next
    }
    in_try {
      line = $0
      gsub(/`|\*\*/, "", line)
      gsub(/^ +/, "", line)
      try_text = try_text " " line
      next
    }
    END { flush() }
  ' "$1" || true
}

watch="${CLAUDE_PROJECT_DIR:-.}/docs/dev/flycards/WATCH.md"
if [ -f "$watch" ]; then
  items="$(card_items "$watch")"
  if [ -n "$items" ]; then
    echo
    echo "=== WATCH — look for these on the next fly ==="
    printf '%s
' "$items"
    echo "Source: docs/dev/flycards/WATCH.md (full pass/fail detail per item)"
  fi
fi

# --- LOCAL card -------------------------------------------------------------
# The sibling of WATCH: rows needing a CONTRIVED condition (a toggle, a specific
# campaign, or something made to happen on purpose), run against the local fly
# every 2-3 days. Split out 2026-08-07 because G29 sat PARTIAL for four weeks and
# then failed to close on the WATCH list too -- it needs a pilot to eject on
# purpose, which the WATCH rules explicitly exclude, so it had been parked on the
# one surface that structurally could not close it. Same parser, same format.
local_card="${CLAUDE_PROJECT_DIR:-.}/docs/dev/flycards/LOCAL.md"
if [ -f "$local_card" ]; then
  items="$(card_items "$local_card")"
  if [ -n "$items" ]; then
    echo
    echo "=== LOCAL card — needs setting up on purpose (every 2-3 days) ==="
    printf '%s
' "$items"
    echo "Source: docs/dev/flycards/LOCAL.md (full pass/fail detail per item)"
  fi
fi

echo "[Claude: present this board to the user near the top of your first reply."
echo " Re-surface BOTH cards whenever the user is about to fly, generate a turn,"
echo " or otherwise test — link docs/dev/flycards/WATCH.md (zero setup, look for"
echo " it in whatever you were flying anyway) and docs/dev/flycards/LOCAL.md"
echo " (needs arranging on purpose). Keep them distinct: offering a LOCAL row as"
echo " if it were opportunistic is what left G29 unclosed for four weeks.]"
