# Per-airframe player startup times

Where the `startup_minutes:` numbers in `resources/units/aircraft/*.yaml` come from, and
what to do before adding one.

Answers upstream issue
[#214](https://github.com/dcs-retribution/dcs-retribution/issues/214), open since 2023.

## The problem

`player_startup_time` is one campaign-wide allowance, 10 minutes by default, applied to
every airframe a player might cold-start. A Viper on a stored-heading alignment and a
Phantom waiting for its gyros to reach 160 °F are not the same aircraft, and one number
cannot be right for both.

Upstream's maintainer asked twice for these to live in the aircraft yamls rather than in a
setting. That is what this is.

## The model

    startup_minutes = INS alignment + a window for other system starts

**Taxi is not in it.** That is `estimate_ground_ops` — 2 minutes off a carrier or FOB, 8
from an airfield — and it varies by field, not by airframe. Putting taxi in both places
would double-count it.

**Alignment means stored heading, not full gyrocompass.** A campaign jet sitting on its own
ramp between turns has not been moved since its last shutdown, which is exactly the
condition stored heading requires. It is also the case the issue was filed about: the
reporter's complaint was that he could cold-start an F-16 *with stored heading*, take off and
bomb Damascus inside the 18 minutes Retribution reserved.

The consequence is that on modern jets **alignment stops being the dominant term** — 40 to 90
seconds against a 10-minute allowance. What is left is the checklist.

## The numbers, and where each came from

| Airframe | Value | Alignment (sourced) | Other |
|---|---|---|---|
| F-16C_50 | **4** | Stored heading ~90 s | ~2 min systems |
| F-15E, F-15ESE | **3** | Stored heading ~40 s | ~2 min systems |
| F-4E-45MC | **9** | HDG Memory 2 min 15 s, **after** a ~4.5 min gyro thermal soak | ~2 min systems |

Sources, all from `references/manuals/`:

- **F-16C** — EA Guide, INS chapter: "Stored Heading Alignment. Rapidly aligns the INS within
  ~90 seconds." Normal gyrocompass is ~8 minutes, for comparison.
- **F-15E** — Manual v1.7: "SH alignment is complete approximately 40 seconds after turn-on
  and should achieve approximately GC align accuracy." The same manual puts the whole
  procedure with a *full* alignment at "10 minutes with only necessary actions performed",
  which is where the ~2 minute systems window below is inferred from.
- **F-4E** — Chuck's Guide: "HDG Memory Alignment: Takes 2 minutes 15 seconds. Only available
  if Stored Heading option is enabled via Mission Editor." The manual adds the part that
  makes the Phantom different: the INS gyros must reach 160 °F *before* alignment can begin,
  heating "at a rate of approximately 20 °F per minute" plus 50 seconds for the HEAT light —
  about 4.5 minutes from ambient with nothing else able to proceed past it.

### The systems window is inferred, not sourced

The ~2 minutes for everything that is not the INS is a **judgement call**, derived by
subtracting an assumed ~8 minute full alignment from the F-15E's stated 10-minute
whole-procedure minimum. No manual states it directly, and the F-15E's own full-alignment
time is not published in the manual we hold. Treat it as the weakest number here. If anyone
stopwatches a real cold start, their measurement replaces this arithmetic.

## Adding a value

1. **Source it.** A manual page, a measured stopwatch run, or a maintainer's stated number in
   an upstream thread. Not a guess, and not an analogy to a similar jet.
2. **Record the source here**, in the table above. The yaml carries the number only.
3. **Leave it out if you cannot source it.** An absent key falls back to
   `player_startup_time`, which is honest. A number that merely looks measured is worse than
   no number.

Airframes deliberately left without a value, having checked: **FA-18C** (the EA Guide
documents the stored-heading option but states no duration), **F-14** (Chuck's Guide says ASH
alignment is "much quicker" but gives no figure; full FINE align is 8 minutes ashore, 9 at
the boat), **AH-64D**, **CH-47F**, **C-130J** (no duration in the manual), **UH-1H** (no INS
at all — it should be well under the default, but nothing states a number).

That leaves 4 of 258 aircraft yamls carrying a value. This is the same shape as the fuel
blocks: a documented procedure plus partial real data beats invented coverage.

## In-game pass

Row **B77**. What CI cannot check is whether the shorter allowance actually leaves the player
enough time on the ramp — the test proves the number reaches the schedule, not that a human
can make it.
