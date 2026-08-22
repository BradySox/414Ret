#!/bin/bash
# SessionStart hook: surface the 414th in-game-pass checklist status board so
# Claude can present it to the user at the start of every session. Read-only;
# prints to stdout, which Claude Code adds to the session context.
set -euo pipefail

md="${CLAUDE_PROJECT_DIR:-.}/docs/dev/414th-ingame-pass-checklist.md"
[ -f "$md" ] || exit 0   # checklist absent (e.g. stale checkout) — nothing to do

# Rows are `### ` headings ONLY. `## ` section headings are not rows, and one of
# them carries a marker ("## E. SOF insert generation · ☑ VERIFIED"), so the old
# `^#{2,3}` scope counted a section as a verified row.
headings="$(grep -E '^### ' "$md" || true)"

# A row's status is the FIRST `<symbol> <WORD>` pair on its heading line.
#
# Matching a symbol+word PAIR, rather than a fixed list of whole markers, is what
# makes this survive someone inventing a marker. `✅ CLOSED` and `☒ CLOSED` were
# both introduced after this hook was written; neither was in the old list, so
# six closed rows matched nothing on their marker and fell through to the
# "(was ☐ UNTESTED" that the checklist's own convention makes every re-verified
# row quote. They were briefed as outstanding work for weeks and inflated the
# untested/partial counts. First-pair-wins still excludes that trailing prose.
read -r -d '' STATUS_FN <<'AWKEOF' || true
function status(s,   m) {
  if (match(s, /(☑|☐|◐|✗|⊘|✖|✅|☒) (VERIFIED|UNTESTED|PARTIAL|REGRESSED|RETIRED|REMOVED|CLOSED)/)) {
    m = substr(s, RSTART, RLENGTH)
    sub(/^[^ ]+ /, "", m)
    return m
  }
  return ""
}
AWKEOF

statuses="$(printf '%s\n' "$headings" | awk "$STATUS_FN"'
  { st = status($0); if (st != "") print st }
')"
count() { printf '%s\n' "$statuses" | grep -cFx "$1" || true; }

echo "=== 414th in-game-pass checklist ==="
echo "verified $(count VERIFIED) | untested $(count UNTESTED) | partial $(count PARTIAL) | regressed $(count REGRESSED) | closed $(( $(count RETIRED) + $(count REMOVED) + $(count CLOSED) ))"
echo

outstanding="$(printf '%s\n' "$headings" | awk "$STATUS_FN"'
  {
    st = status($0)
    if (st == "UNTESTED" || st == "PARTIAL" || st == "REGRESSED") {
      line = $0; sub(/^#+ +/, "", line); print line
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

# --- the fly cards ----------------------------------------------------------
# Two standing cards, same format, parsed by one function so they can never
# drift apart: WATCH (closes from ordinary flying) and LOCAL (needs a contrived
# condition arranged on purpose). Items are the `### ` headings; the `**Try:**`
# paragraph under one says how to make it happen and is printed with it, because
# 2026-08-06 an item came back unanswered purely because its heading named two
# row IDs and no observable. A Try may wrap across source lines; it is joined and
# ends at the first blank line. An item with no Try still prints its heading.
#
# Only items in a LIVE section are printed. A closed item is moved to a `## Done`
# section (LOCAL) or to ARCHIVE.md (WATCH) — but the old parser read every `### `
# in the file, so LOCAL's two CLOSED items were briefed as live work for two
# days after they were closed. That is the "it doesn't update when something is
# checked off" failure, and it is the same class as the marker bug above: the
# card was crossed off correctly and the reader was told otherwise.
card_items() {
  awk '
    function flush(   t) {
      if (heading == "") return
      if (live) {
        print "  " heading
        if (try_text != "") {
          t = try_text
          gsub(/^ +| +$/, "", t)
          print "      Try: " t
        }
        n_printed++
      }
      heading = ""; try_text = ""; in_try = 0
    }
    # A section heading opens or closes the live list. Anything filed under Done,
    # Archive, Dropped, Closed, Superseded or the parking lot is history, not work.
    /^## / {
      flush()
      live = ($0 !~ /^## *(Done|Archive|Archived|Closed|Dropped|Superseded|Parking)/)
      next
    }
    /^### / {
      flush()
      heading = substr($0, 5)
      gsub(/`|\*\*/, "", heading)
      # Belt and braces with the section rule: an item crossed off in place still
      # says so in its own heading.
      if (heading ~ /(CLOSED|OFF THE CARD|DONE|VERIFIED)/) heading = ""
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
    END { flush(); if (n_printed == 0) print "  (empty — nothing on this card)" }
  ' "$1" || true
}

print_card() {
  local file="$1" title="$2" source="$3"
  [ -f "$file" ] || return 0
  echo
  echo "$title"
  card_items "$file"
  echo "Source: $source (full pass/fail detail per item)"
}

print_card "${CLAUDE_PROJECT_DIR:-.}/docs/dev/flycards/WATCH.md" \
  "=== WATCH — look for these on the next fly ===" \
  "docs/dev/flycards/WATCH.md"

print_card "${CLAUDE_PROJECT_DIR:-.}/docs/dev/flycards/LOCAL.md" \
  "=== LOCAL card — needs setting up on purpose (every 2-3 days) ===" \
  "docs/dev/flycards/LOCAL.md"

echo
echo "[Claude: present this board to the user near the top of your first reply."
echo " Re-surface BOTH cards whenever the user is about to fly, generate a turn,"
echo " or otherwise test — link docs/dev/flycards/WATCH.md (zero setup, look for"
echo " it in whatever you were flying anyway) and docs/dev/flycards/LOCAL.md"
echo " (needs arranging on purpose). Keep them distinct: offering a LOCAL row as"
echo " if it were opportunistic is what left G29 unclosed for four weeks.]"
