# Substrate inventory — R0

Status: **R0 of `414th-campaign-architecture-notes.md` — done 2026-08-20.** The rung's job:
map every campaign-persistent quantity to its writers, readers, and cockpit path, and let
the substrate spec fall out. Method: code sweep of `game/` on main @ `a0ed0b007`, receipts
as file:line. The falsifier pre-registered for this rung — *"the inventory finds the
quantities already coherent — then the substrate is a rename, do less"* — **partially
fired**; §4 records what that changes.

## 1. Stocks (counted per node)

| Quantity | Home | Writers | Readers | Cockpit path | Verdict |
|---|---|---|---|---|---|
| Ground units per CP | `Base.armor` (`game/theater/base.py:10`) | procurement deliveries, FLOT losses, §56 motorpool strikes, transfers | ground planner (`deployable_armor`/`reserve_armor_for`), front-line math, §56 render, transfers | kill armor at the FLOT; bomb the motorpool | **citizen** — the core stock |
| Base strength (0–1 per CP) | `Base.strength` (`base.py:11`) | strike damage (`basedamage.py:71`), per-turn recovery × `SupplyStatus` | front-line position math (`frontline.py:298–314`) | bomb the base; cut its supply | **citizen** — carries the substrate's first flow-coupling |
| Squadron pilots | `Squadron.available_pilots` | losses, per-turn replenish, CSAR returns | flight planning, UI | losses; rescues | citizen; replenish ignores supply (§4 gap 3) |
| Squadron airframes | `Squadron.owned_aircraft`/`untasked_aircraft` | procurement, losses | planner, UI | shoot them down | citizen; same gap |
| Naval anti-ship magazines (§81) | `game/fourteenth/naval_magazines.py` persisted state | mission expenditure | its own release logic + surfaces | empty their tubes | **private ledger** — one feature reads it |
| Cruise-missile stocks (§63) | `cruise_raids` state channel | raids, call-for-fire | its own raid logic + surfaces | fire them | **private ledger** — second separate mechanism |
| Ammo depots → front-line capacity | `ControlPoint.frontline_unit_count_limit` (`controlpoint.py:1283–1298`) | depot kills | ground planner limit, `theaterstate.py:184`, `attackbuildings.py` | bomb the depot | **citizen — the reference stock→capacity coupling** |
| Runway state | `RunwayStatus` (`controlpoint.py:336`) | strikes; budget-funded repair over turns | 7 files: squadron ops, packagebuilder, transfers, assigners | crater it | citizen |
| §56 reserve | derived from `Base.armor` (`reserve_armor_for`) | — | motorpool populate + targeting | bomb the depot | citizen — deliberately a view, never double-counted |

## 2. Flows (moving on edges)

| Quantity | Home | Writers | Readers | Cockpit path | Verdict |
|---|---|---|---|---|---|
| Income → budget | `game/income.py` (alive `REWARDS` buildings + CP income) → `Coalition.budget` | turn income; spends | procurement, runway repair, §68 SAM repair, player purchases | capture CPs; bomb income buildings | **citizen — an economy already exists and is coupled** |
| Unit purchase pipeline | `GroundUnitOrders` / pending deliveries | procurement, player UI | arrival into `Base.armor`, mission results | interdict the convoy; §5.1 for the factory hole | citizen; local production is its one ungated edge |
| Unit transfers | `game/transfers.py` (`TransferOrder`, `Convoy`, `CargoShip`) | ground planner, player | convoy/ship generation, §35/§50/§78 interdiction, arrival | shoot the convoy | **citizen — the one fully-realized edge flow** |
| Supply status | `game/theater/supply.py` (derived per CP per turn) | derived from transit network | strength recovery multiplier (today its only consumer) | cut the route | citizen; R2 adds its second reader |

## 3. Out of the substrate (deliberately)

Fog/`discovered_by_player` (seam 2's audit stands: intel stays three-rules-small) · weather
(§47 environment, not war state) · COMINT tier and §51's captured-aircrew gate
(feature-local, single-reader by design) · §75 victory state (a consumer of quantities, not
one) · `red_tempo:` windows (authored input) · §89 cycle timing (scheduling) · §93 region
priorities and the doctrine settings (command inputs, already planner-read) · downed pilots
+ survival clock (feature-owned roster; CSAR reads it everywhere it should).

## 4. Findings

1. **The core substrate already exists and is healthy.** `Base.armor`, strength,
   income→budget, transfers, runway state, and the ammo-depot capacity coupling form a
   multi-reader, cockpit-coupled web — upstream's own architecture, extended by §90/§56/§68.
   The graveyard diagnosis sharpens: §53 died as a *second* economy bolted beside the real
   one; §54 died as a stock nothing fed *while income-producing buildings already worked*.
   The admission rules were being enforced by upstream's design all along.
2. **Exactly two private ledgers exist** — §81's naval magazines and §63's cruise stocks,
   parallel persistence mechanisms one feature each reads. The parked SAM magazines would
   have been the third. That is the whole consolidation surface.
3. **The value is in five missing couplings, not consolidation:**
   1. Income is not route-coupled — an ISOLATED CP still pays full income.
   2. Unit-delivery arrival vs supply state — **answered, §5.1**: transfers are gated, but a
      factory on a cut-off CP produces at full rate. Folds into gap 1, not its own fix.
   3. Pilot/airframe replenishment ignores supply entirely.
   4. Combat effectiveness ignores supply — already scoped as R2.
   5. Magazines do not resupply via flows — R3's actual design space.
4. **The falsifier partially fired, so R1 changes shape.** A big behavior-identical
   `TheaterState` refactor is not justified by the evidence — there is no pile of private
   ledgers to unify. R1 shrinks to: one persistence home for magazine stocks (absorbing §81
   + §63, ready for SAM), plus the coupling table above as the build list. Cheaper, less
   risk, same architecture — the pillars, admission rules and R2–R7 stand unchanged.

## 5. Open questions

| # | Question | Owner |
|---|---|---|
| 1 | Does a delivery to an ISOLATED CP arrive today? (gap 2) | **ANSWERED 2026-08-20 — §5.1** |
| 2 | Should income route-couple (gap 1), and at what fraction — the §90 rung-A 1.0/0.25/0.0 ladder? | DM call at R1 |
| 3 | Magazine home: extend the §81 state shape or a new `TheaterStocks` owner both migrate into? | R1 design |

### 5.1 Question 1 — local production arrives, anything shipped in does not

Traced on main @ `a0ed0b007`. **Deliveries are already network-gated. The one unconditional
path is a factory standing on the destination control point itself.**

All three cases run through `GroundUnitOrders.process` (`game/groundunitorders.py:56`), called
from `ControlPoint.process_turn` (`game/theater/controlpoint.py:1175`):

| Destination | Path | Arrives? |
|---|---|---|
| Cut off, factory alive on the CP | `find_ground_unit_source` short-circuits to the destination (`groundunitorders.py:122` → `can_recruit_ground_units` → `has_factory`, `controlpoint.py:738`); units land via `base.commission_units` (`groundunitorders.py:90`) | **Yes — same turn, full rate, supply never consulted** |
| Cut off, no factory, none reachable | `find_ground_unit_source_in_network` finds no source (`groundunitorders.py:139`) → refund + "lost its source for ground unit reinforcements" | No — money back |
| Cut off, no factory, factory inside the pocket | `TransferOrder` → convoy over the pocket's own roads | Yes, and correctly — it drove there |

Anything shipped in is gated twice, and both gates bite:

- `PendingTransfers.arrange_transport` (`game/transfers.py:633`) picks the transport from the
  first hop's link type. An Airlift hop needs a TRANSPORT squadron able to operate at both ends
  (`AirliftPlanner.compatible_with_mission`, `transfers.py:288`). With none, `transfer.transport`
  stays `None`, `TransferOrder.proceed` (`transfers.py:228`) returns early, and the units sit at
  the origin, retried every turn by `plan_transports`.
- A route that dies mid-transit disbands the transfer where it stands
  (`disband_uncompletable_transfers`, `transfers.py:755`), commissioning the units at their
  current position, not the destination.

**ISOLATED is rarer than the question assumed, and that makes the hole bigger, not smaller.**
`_reaches_rear` BFSes through frontline control points (`supply.py:53–72`), and
`TransitNetworkBuilder` links every friendly airfield with an operational runway to every other
one (`transitnetwork.py:186–195`). So one intact strip anywhere in a cut-off pocket reaches the
rear and downgrades the whole pocket to AIRLIFTED. ISOLATED needs the pocket to hold no
operational runway at all — a FOB with no helipads and no ground spawns
(`Fob.runway_is_operational`, `controlpoint.py:1815`), or an airfield whose runway is cratered
(`Airfield.runway_is_operational`, `controlpoint.py:1442`). But an AIRLIFTED factory produces
unconditionally too — nothing on that path reads `SupplyStatus` either — so the common case is
the leaky one.

**Recommendation: R1 carries no delivery-gating fix.** A factory in an encircled pocket
producing locally is defensible on its own terms. What is not is that the pocket buys that armor
from a theater-wide budget it also still pays into at full rate. That is gap 1, not gap 2 — the
two gaps are one coupling seen twice, and income is the cheaper place to cut it. If a production
gate is wanted anyway, the seam is `can_recruit_ground_units` (`controlpoint.py:728`): one
`SupplyStatus` read, no new mechanism.

**Found alongside, not acted on.** `ENEMY_BASE_STRENGTH_RECOVERY = 0.05` (`game/game.py:95`) is
read nowhere in the tree — the only `affect_strength` top-up applies
`PLAYER_BASE_STRENGTH_RECOVERY` to `theater.player_points()` (`game.py:576`). Red bases take no
per-turn strength recovery at all. Inherited from upstream; rung A's gate is therefore the only
recovery rule in play, not a blue-side asymmetry.
