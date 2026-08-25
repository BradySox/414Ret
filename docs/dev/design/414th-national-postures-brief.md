# National Postures Research — Handoff Brief

**This file is a task prompt.** Paste it (or point a fresh session at it) to run the
research. It carries every decision already made, so do not re-ask them. When the
research lands, its permanent home is `414th-national-postures-notes.md` + the data
table; this brief is then superseded.

**You may ask Brady clarifying questions before starting** — one round, batched via
the AskUserQuestion widget. If nothing is genuinely blocking, start.

## The mission

Build the historical-relations data that lets §96 (bordering-nation airspace) work
with **zero campaign authoring**: given only a campaign's terrain, start date and
factions, the engine should know each bordering nation's posture toward each side.
Deep-dive US relations — and Soviet/Russian relations — with every nation that has
territory on a DCS map, from the Vietnam era (~1955) to the present, expressed as
dated posture ranges.

## Decisions already made (DM, 2026-08-25 — do not re-litigate)

| Question | Decision |
|---|---|
| Deliverable | A machine-readable table in the repo that the feature reads, plus a sourced design note |
| Perspective | Both blocs: posture toward the US-led side AND toward the USSR/Russia-led side |
| Scope | Every nation with territory on a real-world DCS map (~40 countries) |
| Buckets | Five: `allied` / `permissive` / `contested` / `closed` / `hostile` |
| Integration | **Automagic**: works on existing campaigns with no yaml. Campaign yaml remains as an override only ("if we or Starfire wish to establish it via the yaml we can") |

## The five buckets — define by overflight consent, not by sympathy

The bucket answers one operational question: *would this nation consent to this
bloc's military aircraft transiting its airspace for the conflict at hand?*
Diplomatic warmth is not the test — France was an ally in 1973 and still denied US
overflight for the Yom Kippur resupply. Date by events (coups, revolutions, wars,
basing agreements), not by decades.

- `allied` — treaty ally or basing host; transit and basing presumed (NATO members
  toward the US bloc, Warsaw Pact toward the Soviet bloc).
- `permissive` — grants overflight/corridors without alliance (Pakistan 2001–2011
  toward the US; Turkmenistan's OEF corridor).
- `contested` — transit sometimes tolerated, sometimes denied; unreliable or
  event-dependent (Pakistan post-2011; 1973-airlift European denials).
- `closed` — refuses transit and defends its airspace, without being a belligerent
  (Iran toward the US post-1979; Switzerland/Austria toward everyone, always).
- `hostile` — an active belligerent or state of war with the bloc (North Vietnam
  toward the US 1955–75; Iraq toward the US 1990–91 and 2003).

**How the feature consumes them today** (do not change code): `allied`/`permissive`
→ overflight allowed; `contested`/`closed`/`hostile` → refused (intercepts). The two
extra buckets are kept because the split will matter later (contested = risky
transit; hostile ≠ closed for future basing/targeting logic). Record all five
faithfully; the collapse happens at read time.

## The table

Target file: `resources/borders/national_postures.yaml`. Draft it in the repo but do
**not** wire any code to it — the wiring is a separate build session. Schema:

```yaml
# §96 national postures: dated overflight/alignment posture per country per bloc.
# Sources and reasoning: docs/dev/design/414th-national-postures-notes.md.
# Buckets: allied | permissive | contested | closed | hostile.
# Ranges are [from, to) by year (month precision as YYYY-MM where a single year
# contains a flip, e.g. Iran 1979). A date not covered by any range = closed.
countries:
  Pakistan:
    toward_us_led:
      - { from: 1954, to: 1965, posture: allied }      # SEATO/CENTO
      - { from: 2001, to: 2011-05, posture: permissive } # OEF ALOC/overflight
      - { from: 2011-05, to: present, posture: contested } # post-Abbottabad
    toward_ru_led:
      - { from: 1954, to: 1991, posture: closed }
    # Optional: the interceptor a §96 alert flight should fly, per era.
    # VANILLA pydcs ids only. Omit where unresearched; the engine has a fallback.
    aircraft:
      - { from: 1965, to: 1990, id: MiG-21Bis }   # F-6/Mirage stand-in, vanilla only
      - { from: 1990, to: present, id: F-16A }
  Switzerland:
    toward_us_led: [{ from: 1955, to: present, posture: closed }]
    toward_ru_led: [{ from: 1955, to: present, posture: closed }]
```

Rules:
- **Uncovered date = `closed`.** The safe default for a border feature is "it
  defends"; never invent a range to fill a gap you did not research.
- Countries that did not exist yet (post-Soviet states pre-1991) simply have no
  ranges before independence; the territory belongs to the predecessor (USSR),
  which must itself be in the table.
- Divided/renamed states get their own entries per era where DCS models them (GDR
  and Germany are different pydcs countries; USSR vs Russia likewise).
- The `aircraft` column is optional and secondary. Capture it where the same
  sources hand it to you; never let it slow the postures work. Vanilla DCS ids
  only (no mods — hard fork constraint).

## Scope: the country list

Every nation with territory on these real-world terrains (fictional-overlay
campaigns are out of §96 scope by standing DM call): Caucasus, Syria, Persian Gulf,
Sinai, Iraq, Afghanistan, Kola, Normandy, The Channel, Germany (Cold War), Nevada,
Marianas.

Starter list — **verify completeness against each map's real extent before
finishing; this list is from memory and that is exactly what this project distrusts**:

- Caucasus: Russia/USSR, Georgia, Armenia, Azerbaijan, Turkey
- Syria map: Syria, Turkey, Lebanon, Israel, Jordan, Iraq, Cyprus (+ UK SBAs), Egypt (edge)
- Persian Gulf: Iran, UAE, Oman, Qatar, Bahrain, Saudi Arabia, Pakistan (edge)
- Sinai: Egypt, Israel, Jordan, Saudi Arabia, Lebanon (edge), Syria (edge)
- Iraq map: Iraq, Iran, Kuwait, Saudi Arabia, Jordan, Syria, Turkey
- Afghanistan: Afghanistan, Pakistan, Iran, Turkmenistan, Uzbekistan, Tajikistan
  (China's Wakhan strip is off the playable area — measured, excluded)
- Kola: Russia/USSR, Norway, Finland, Sweden
- Germany CW: FRG, GDR, Czechoslovakia, Poland, Denmark, Netherlands, Belgium,
  France, Austria (verify extent), Luxembourg (verify)
- Normandy/Channel: France, UK, Germany (WWII-era is out of posture scope — start
  the clock at 1955; these maps mostly matter for the border *drawing*, not eras)
- Nevada: USA only
- Marianas: USA (Guam/CNMI), Japan (verify extent)

A nation on the list that DCS does not model as a pydcs country (Turkmenistan,
Uzbekistan, Tajikistan, Kuwait — verify) still gets postures: a permissive one
spawns nothing and needs no pydcs country, which is precisely how those become
drawable at all.

## Method and standards

- **Per country: a dated timeline first, buckets second.** Anchor each range
  boundary to a named event (Iranian Revolution 1979-02; Egypt's realignment
  1972–79; Iraq 1958 coup / 1990 Kuwait / 2003; Pakistan 1965, 1971, 1979, 2001,
  2011). The notes file carries the reasoning and sources; the yaml carries only
  the result.
- **Cite sources in the notes file** — state department history, declassified
  basing/overflight agreements, reputable histories. No source, no range: default
  stays `closed`.
- **Both blocs for every country, even when one side is boring** ("closed toward
  the USSR for the entire period" is a finding, not filler).
- **Write plain** (repo standard): one fact per line, no drama, no voiceover.
- **When the evidence contradicts an assumption in this brief, lead with that** —
  including the starter list and the schema.
- Deliverables land as: `resources/borders/national_postures.yaml` (draft, unwired)
  + `docs/dev/design/414th-national-postures-notes.md` (sources + reasoning + the
  open questions for the DM). Update the design-note index in `CLAUDE.md` and
  mirror to `AGENTS.md` per the sync convention. **No code changes** in that
  session.

## Context you need but must not rebuild

§96 is built and flying: real-data border polygons, alignment **derived** from who
holds the airfields inside each border (red/blue-aligned nations are drawn in their
side's colours; red-aligned airspace joins §1's QRA accept zones), and a per-zone
`overflight` flag separating "neutral that permits transit" from "neutral that
intercepts". Read `414th-neutral-border-defense-notes.md` first. This research
replaces the hand-authored `overflight` flag with date-resolved truth; the derived
alignment stays exactly as is (a nation hosting a campaign's airfields is aligned
regardless of any table).
