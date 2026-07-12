# 414th — SAM site realism directions (design notes)

**Status: DESIGN ONLY — no code.** Follow-on to feature **§60** (SAM guidance-radar redundancy). §60
gave every SAM layout a second engagement radar so a single HARM stops being a functional site kill;
this note is the honest accounting of *what §60 abstracts away* and the three real-world directions
that would push SAM sites toward authenticity, each with a decisive verdict so a future session
knows whether it is worth opening. Prompted by the Air Power Australia "Russian/Soviet SAM Site
Configurations" satellite-imagery studies (Kopp / Sean O'Connor).

**The framing §60 established, and the tension to protect.** §60's doubling is a **balance
abstraction**: a real *battalion / fire unit* of a legacy system fields exactly **one** engagement
radar (one Fan Song, one Low Blow, one 1S91 Straight Flush, one Flap Lid). Real survivability comes
from having **many fire units**, not two radars bolted to one. §60 reads closest to reality on the
**strategic systems** (S-300/S-400, Patriot), where a battalion group / regiment genuinely fields
multiple radars. The load-bearing tension for everything below: **§60 and Direction B both add
radars.** If a regiment model ever lands for a strategic system, §60's doubling must be **reverted
for that system** — never stack them, or one "site" carries four engagement radars nothing in the
real world ever did.

---

## Direction A — revetment-geometry authenticity  ·  verdict: LOW PRIORITY

**What APA teaches.** Real strategic SAM sites have signature ground patterns, legible from orbit:
the SA-2's six-point "Star of David" (6 launchers hexagonally around one central Fan Song), the SA-3's
compact 4-rail cluster (very often nested inside an SA-2 regiment), the S-300P's radial "flower/clover"
of TEL hardstands fanned around the engagement radar, the SA-5's sprawling fans of rail launchers with
Square Pair radars, footprints in the hundreds of metres.

**Where we are.** Our shared templates (`8_Launcher_Circle`, `6_Launcher_Circle/Semicircle`,
`S-300_Site`, `2_Launcher`, `Patriot_Battery`) already lay launchers out **radially** around the
radars, so the *shape* is a reasonable abstraction of the real thing — an S-300 on `8_Launcher_Circle`
reads as a rough flower, an SA-2 on `6_Launcher_Circle` as a rough ring.

**Why it's low priority.** The templates are **shared across many systems** (an SA-2, SA-3, SA-5,
S-350, NASAMS-3 and Sky Sabre all ride `8_Launcher_Circle`), so no single geometry can match every
tenant's real signature at once. True per-system authenticity means **per-system `.miz` templates** —
real maintenance cost, more `.miz` files to keep in lockstep with their YAML, for a payoff that is
cosmetic (the player sees it on the F10/ME map, not in a merge). The gameplay footprint is already
handled: launchers are dispersed enough that one bomb doesn't clear a site.

**Verdict.** Don't retrofit the shared templates. If we ever want it, do **one** marquee system as a
showcase — a dedicated `S-300_Flower.miz` or an authentic SA-2 hexagram — behind its own preset, and
only if a squadron member actually asks to *see* it. Not worth a broad pass.

---

## Direction B — regiment-level redundancy (the faithful alternative to §60)  ·  verdict: DEFER, but this is the "right" long-term model

**What APA teaches.** A real air-defense *regiment* is several **battalions** (fire units), each with
its **own single** engagement radar, netted to a **shared** long-range acquisition radar (Big Bird /
Clam Shell) and a command post (Senezh / Baikal). Redundancy is **N fire units**, not two radars on
one. Kill one battalion's Flap Lid and that battalion is blind — but the regiment fights on because
the other battalions and the shared acquisition picture are intact.

**The engine already half-models this.** Retribution places **multiple SAM TGOs per control point**,
and MANTIS **nets them** into one IADS with shared early-warning and C2 (the §51/§52 comms/command
graph). So the faithful regiment picture largely **emerges at the campaign-authoring layer**: author a
CP with three single-radar SA-3 sites + one EWR, and MANTIS gives you a three-fire-unit regiment that
survives losing any one radar — *without* §60's per-site doubling.

**Why defer.** Making this a first-class *modeled* construct (a "regiment" object that owns its
battalions + shared acquisition, priced/placed/repaired as a unit) is a real engine change touching
placement, MANTIS wiring, the buy menu and save format — large, and mostly duplicating what emerges
from placing several sites plus MANTIS. The cheap 80 % is a **campaign-authoring guideline**, not
code: "for a strategic belt, place a few single-radar fire units + a shared EWR rather than one fat
doubled site."

**Verdict.** Keep §60 as the pragmatic per-site fix for the **legacy/mobile** systems (SA-2/3/6, Hawk
— where a lone site is common and a single-HARM kill is the real complaint). For **strategic** belts,
prefer the **regiment-by-authoring** pattern in new campaigns. **Guardrail:** if we ever build the
regiment construct for a strategic system, revert §60's doubling for that system so radars aren't
double-counted. Record which systems are "regiment-modeled" vs "§60-doubled" the day that starts.

---

## Direction C — acquisition-radar separation + radar decoys  ·  verdict: separation MAYBE (small), decoys PARK (DCS blocks it)

**C1 — push the acquisition radar off the fire unit.** Real sites site the acquisition / EWR radar
well away from the engagement radar and launchers (survivability, clutter, and because it feeds the
*regiment*, not one battalion) — often hundreds of metres to kilometres out. Our search-radar slot
sits ~30–60 m from the engagement radar, co-located inside the same TGO. Pushing it out is a **small,
low-risk template tweak** (a further-out position in the `.miz`, same as §60's second-radar
positions) and it *reads* more real on the map. Caveats: it's still one TGO to MANTIS and the DCS
engagement model, so it's mostly cosmetic + a slightly larger footprint; and on the truly strategic
systems the "separate acquisition radar" is better represented as a **separate EWR site** (which is
Direction B, and which we already support). **Verdict: MAYBE** — a nice touch to fold into the S-300
template if we ever revisit it, not worth its own pass.

**C2 — radar decoys (inflatable / mock emitters).** Russian doctrine leans hard on decoys to soak
anti-radiation missiles. **DCS makes a *functional* decoy hard to impossible**: a HARM/anti-radiation
weapon in DCS homes on an **emitting** radar. A cheap static mockup **doesn't emit**, so it never
draws a HARM — it's pure scenery. A decoy that **does** emit is, by definition, a real radar (real
cost, real threat contribution, and it would actually guide) — not a decoy. Faking "an emitter that
looks like a threat to the HARM seeker but isn't a real SAM radar" would mean scripting the ARM's
target selection, which the sim doesn't expose. **Verdict: PARK.** The one honest cheap version — a
cosmetic mock radar that soaks nothing — teaches the player the wrong lesson (they'd waste a HARM on
scenery, or learn to ignore it), so it's worse than nothing. Revisit only if ED ever exposes ARM
seeker decoy behavior.

---

## One-line summary for the next session

§60 (doubled engagement radar) is the shipped, pragmatic anti-single-HARM-kill fix and is honest as a
balance call. If realism ever gets a real budget: **B** (regiment-by-authoring for strategic belts) is
the correct long-term model and the only one worth engine work — **A** and **C** are cosmetic and
mostly not worth it, with **C1** the one small tweak worth folding into a future S-300 template pass.
Never run §60 doubling and a regiment model on the same system.
