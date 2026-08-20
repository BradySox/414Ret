# SCAR — "Sandy" rescue escort

> # ⛔ REMOVED — historical record only
>
> **Everything on this page was removed from 414Ret on 2026-08-07 and no longer exists.**
> `FlightType.SCAR`, the Sandy rescue-escort role, the King + Jolly Green + Sandy package,
> the `combatsar-config.lua` runtime, the survivor ledger, the enemy snatch party, and the
> `auto_combat_sar` setting are all gone. The fork replaced its own combat-SAR (§21) and this
> escort (§15) wholesale with upstream `dcs-retribution#929`. A saved Sandy flight loads as
> CAS; a saved Combat SAR flight loads as the upstream rescue.
>
> **What to read instead:** **[Combat SAR](Combat-SAR)** — the rescue that ships now. It is a
> single helicopter task (`FlightType.CSAR`) with no escort element and no on-scene commander.
> There is no Sandy role to fly.
>
> This page is kept **only** so that older design notes, saves, and briefings that reference
> the machinery can still be understood. **Do not author against it, and do not use it as a
> model for new work.**

---

SCAR is the **rescue-escort ("Sandy")** role inside the fork's combat-SAR package. When a friendly
pilot is down, a SCAR flight gets eyes on the survivor, **suppresses the threats around them**, and
**walks the rescue helo in** — the classic USAF "Sandy" job. It is flown on the **A-10C** or
**AH-64D**, the airframes built to loiter low over a survivor and trade fire with whatever is
trying to reach them.

> **This is a rework.** SCAR used to be a moving-armor *hunt* (find the real high-value target
> among look-alike decoys). That armor-hunt scenario — and its auto-planner — were **retired on
> 2026-06-27** and the task was repurposed into the rescue-escort role described here. The fork's
> conventional anti-armour task is **BAI**, which is unchanged. If you came here looking for the
> old "hunt the SCUD/convoy" mission, it no longer exists.

> **In-game-pass status:** the planner side is CI-tested; the enemy-capture race is flown-verified
> (G20). The Sandy AI divert (G23) is frozen pass-or-delete per the 2026-07-03 CSAR rescope; a
> captured pilot is a held POW (no recovery-raid mission — see [Combat SAR](Combat-SAR)).

---

## The combat-SAR package

SCAR is one element of a three-part package, modelled on real combat-SAR doctrine:

| Element | Role | Airframe |
|---|---|---|
| **King** | Airborne mission commander — TACAN beacon, F10 survivor locator (LARS), voice cueing | C-130J |
| **Jolly Green** | The rescue / pickup — flies in, lands, boards the survivor, delivers them home | Rescue helo (CH-47…) |
| **Sandy** ×2–4 | **RESCAP escort** — protect the survivor, kill the threats around them, walk Jolly in | A-10C / AH-64D (`FlightType.SCAR`) |

The full package is **1 King + 1 Jolly Green + 2–4 Sandy**, planned by you off the FLOT. The
King and Jolly Green are the
[Combat SAR](Combat-SAR) flight types; **Sandy is `FlightType.SCAR`**. See
[Combat SAR](Combat-SAR) for the rescue mechanics, the King's beacon/LARS, and the rescue scoring
that spares the aviator at debrief.

---

## Flying Sandy

`FlightType.SCAR` is **player-selectable** when you build a package, eligible on the A-10C and
AH-64D. Your job over the survivor:

- **Hold with the King and Jolly.** The King is the on-scene commander — it smokes/marks the
  threats and talks the picture. Work to its cues.
- **Suppress the threats around the downed pilot.** AAA, MANPADs, and any enemy ground party
  closing on the survivor are yours to put down so the helo can get in.
- **Watch for the snatch party.** On an ejection the enemy may send infantry to **capture** the
  survivor (red smoke + a MAYDAY cue). Kill it before it reaches the pilot — if it dwells on the
  survivor un-rescued, the pilot is **captured** and becomes a POW. (Full detail in
  [Combat SAR](Combat-SAR).)
- **Walk the helo in.** Keep the threats down and clear the run-in so Jolly Green can land, board,
  and extract.

A Sandy kneeboard page carries this role guidance — holding with the King/Jolly, suppressing
around the survivor, and walking the rescue helo in.

---

## AI standing alert

The AI fields SCAR only as part of the combat-SAR standing alert. With the **`auto_combat_sar`**
setting on (HQ automation, **default ON** since the 2026-07-03 rescope; existing campaigns keep
their saved choice), the planner proposes the package — **1 King + 1 Jolly
Green + 1 Sandy** — so a downed pilot has escort overhead instead of an orbiting helo with no
protection. A free Sandy degrades gracefully: if no A-10/Apache is available, the alert simply
skips it. There is no separate SCAR auto-planner, and **BAI is untouched** — retiring the old SCAR
auto-planner handed every enemy battle position back to BAI.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `FlightType.SCAR` | player-selectable | Build a Sandy rescue-escort flight (A-10C / AH-64D) |
| `auto_combat_sar` | ON | AI standing alert: King + Jolly Green + 1 Sandy when a rescue is needed |

## See also

- [Combat SAR](Combat-SAR) — the rescue package, the King beacon/LARS, capture race, and scoring
- [TARPS Reconnaissance](TARPS-Reconnaissance)
- [Mission planning](Mission-planning)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
