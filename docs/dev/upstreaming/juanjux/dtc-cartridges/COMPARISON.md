# DTC cartridges — the premise he declined on has been falsified

Not a carve. A correction to one line in his inventory, with the evidence behind it.

## What his ledger says

`inventario_fork_414ret.txt`, entry `[A] #1` (DTC export), decision **NO**:

> Motivo NO: el auto-load al inicio de misión de ED está ROTO -> carga manual por
> salida; default ON pese a los docs. Poco práctico hoy.
>
> Flip a SÍ si: ED arregla el auto-load del DTC.

("ED's mission-start auto-load is BROKEN → manual load per sortie. Not practical today.
Flip to YES if ED fixes DTC auto-load.")

## What we measured

Our row **B28 went ☑ VERIFIED on 2026-08-21**, and the pass criterion is explicitly
*with no MUMI/DTC-page interaction*: the jet spawns with COMM1/COMM2 presets carrying the
mission frequencies, steerpoints loaded with names, and on a carrier flight the
TACAN/ICLS/ACLS pre-tuned.

Auto-load fires. It was never broken in the way the ledger records.

## The mechanism, which is the actual answer

It is not a DCS fix — it is a per-unit block that has to be written into the `.miz`, and
upstream does not write it. Both halves are required:

```lua
["Cartridges"] = { [1] = { ["default"] = true, ["name"] = <name> } },
["AutoLoad"]   = true,
```

plus the cartridge itself as `DTC/<name>.dtc` inside the mission zip.

A cartridge present with no `AutoLoad` is exactly the behaviour his note describes:
it shows up on the DTC page and waits for a manual load. So the observation was real;
the diagnosis attributed it to ED rather than to the missing block.

The mechanism was reverse-engineered from a hand-built MP mission flown 2026-07-18 that
pre-loaded a Hornet with zero pilot action, then replicated 2026-07-19.

## Two caveats we still carry, so he does not inherit them blind

1. **Spawn paths.** The reference mission used plain ramp starts. Our own spawn set
   includes uncontrolled-at-t=0 carrier clients and late-activated delayed flights, and
   whether `AutoLoad` fires on *those* is still owed. If it fails only there, the fix
   direction is a spawn-type carve-out, not a format change.
2. **pydcs drops the block on re-save.** Units re-serialize from parsed fields only, so
   §74 carries two shims (`game/missiongenerator/dtc/cartridge.py`): a `FlyingUnit.dict`
   wrap and a post-`Mission.save` zip append. The proper fix is
   [dcs-retribution/pydcs#39](https://github.com/dcs-retribution/pydcs/pull/39), open.
   When it lands, `cartridge.py` shrinks to the model plus the builders.

## Scale, if he reconsiders

`game/missiongenerator/dtc/` is 2,388 lines: 132 cartridge plumbing, 530 shared, 117
generator, and one builder per jet — Hornet 420, Viper 385, Tomcat 794. Pure Python, no
Lua, no MOOSE. The Super Hornet was deliberately dropped (no SA table; its comms and
route already reach it through the miz).

## What we are actually asking

Nothing. The ledger entry is his to keep or flip — the correction is that its stated
flip condition ("if ED fixes auto-load") has no fix to wait for. If he still says no on
practicality, that is a different and entirely defensible answer.
