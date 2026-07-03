# The Retribution UI

This page is a tour of the main 414Ret window so you know where to click. Retribution runs outside DCS as a desktop app: the center of the screen is a live theater **map**, the edges and top hold the controls for planning a turn, and a series of dialogs let you inspect the enemy, build packages, and read the debrief. The workflow is map-centric — most planning starts by clicking something on the map or by opening a panel from the toolbar.

![The 414Ret main window: the campaign control strip across the top, the ATO/packages and flights panels down the left, the live theater map in the center, the unified map layers panel at right, and the info panel along the bottom](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/ui-overview.jpg)

*The main window during turn planning on Germany — Red Tide: top control strip, the ATO/packages and flights columns on the left, the live map (here showing a clicked SAM site's intel popup), and the map layers panel on the right.*

If you are brand new, read [Getting Started](Getting-Started) first, then come back here for the layout.

## The map

The map is the heart of the application. It shows the theater, your bases and the enemy's, the front line (FLOT), known ground objects and air defenses, and the routes of planned flights. You interact with it directly:

- **Click a base, ground target, or front-line sector** to select it and open its context — selecting an objective is usually the first step in fragging a package against it.
- **Click an air-defense site or known enemy ground object** to open its intel/target dialog (see below).
- **Right-click blank map space** to reach the drop-spawn unit-placement tool, a 414th sandbox feature gated behind cheat settings; right-click a unit you placed to remove it. See [Map Layers and Interface](Map-Layers-and-Interface).

The fork makes the map easier to read: SAM rings, emitters, routes, and IADS links are clearer, and short-range mobile defenses are kept off player datalinks while deliberate-SEAD-sized sites stay visible.

Two campaign-state overlays ride on the map. The **campaign-status ribbon** across the top shows the campaign name, turn, date, and the current **[campaign phase](Campaign-Phases-and-ROE)** (click it to expand the whole arc and its objectives; on a political-will campaign the will meters live here too). On a campaign with an active ROE layer, the map also draws the **restricted / weapons-free zones** (dashed red / dashed green), and locked targets wear a **RESTRICTED — ROE badge** on their tooltip. You can also **right-click an enemy supply route** to frag an interdiction package against it.

## The top toolbar and menus

The toolbar across the top is your campaign control strip. From here you:

- **Save and load** the campaign, and start a **New Game** (the wizard described in [Getting Started](Getting-Started)).
- Open **Settings** — the difficulty, doctrine, plugin, and cheat options. The fork reorganised this screen into focused pages (Difficulty & Realism · Air Doctrine · Campaign Management · Mission Generation · Kneeboards · Performance · **Vietnam Ops**) with one-click **difficulty presets** (Casual / Normal / Veteran / Ace) on the Difficulty & Realism page; a settings audit also removed dead/duplicate options and merged the AI-radio toggles into a single **AI wingman radio behavior** choice. Doctrine settings here expose the fork's air-defense, SCAR, and unpredictability knobs.
- **Generate the mission / take off** — produce the `.miz` for the current turn and hand off to DCS.
- **Advance the turn / fast-forward** — resolve and move the campaign forward after a mission, or let the AI auto-resolve.
- Open the **Air Wing** and finance/intel summaries for the current state.

## The ATO and packages panel

The **Air Tasking Order (ATO)** lists every package you have planned for the turn, and each package lists its flights. This panel is where a turn's plan lives:

- A **package** groups flights with a shared objective and timing (for example a strike with its escort and SEAD).
- Selecting a package or flight shows its task, time-on-target, player slots, departure base, squadron fit, available aircraft, and target distance — the fork surfaces this without making you hunt across windows.
- From here you add flights, set tasks (including the fork's tasks: **JAMMING**, **TARPS**, **SCAR**, and **Combat SAR**), choose loadouts, and edit waypoints/altitudes.

For the full planning workflow — building packages, flight plans, escorts, and timing — see [Mission Planning](Mission-planning).

## The unified map layers panel

In the upstream app, map display is controlled by two separate stock Leaflet controls. **The 414th fork replaces both with a single dark-themed, grouped, collapsible map layers panel** that matches the rest of the UI. From it you can:

- Toggle layers (threat zones, navmesh, terrain, enemy intel, routes, and more), with advanced groups collapsed by default.
- Apply one-click **preset views**: **Default**, **SEAD**, **Recon**, and **Clean**, each enabling a useful set of layers for that job.
- Flip the transient **Reveal fog of war (overview)** toggle in the enemy-intel group. This shows ground truth — full enemy composition, threat rings, and otherwise-hidden command posts — as a view-only override. It never changes the campaign and is never saved.

Your layer choices are remembered between sessions (the fog overview is the deliberate exception). Full details are on [Map Layers and Interface](Map-Layers-and-Interface).

## Intel and target dialogs

Clicking a ground object or air-defense site opens an **intel/target dialog**. The fork's panel shows known strength, mission suitability, weapon and detection ranges, IADS membership, visibility, and capture/purchase state.

Intelligence here is deliberately incomplete: in 414Ret an enemy site can be *known to exist* without its exact composition, strength, damage state, or threat rings being known until you attack or scout it, and confirmed battle damage may require a surviving recon (TARPS) pass. If you need the real picture for planning, the **Reveal fog of war** toggle in the layers panel un-fogs these dialogs along with the map.

## The debrief

After a mission, the **debrief** opens with **mission impact first** — territorial changes, runway and base damage, and losses — before the full event-by-event detail. This is where you confirm what the turn cost and gained before advancing. The Combat SAR feature also resolves here: a downed human pilot you recovered and delivered to a friendly field is spared at debrief (you still lose the airframe, but the aviator returns to the squadron).

![The debrief's Casualty report, leading with a Mission Impact block — mission status, bases lost/captured, runway damage — above the per-side loss lists for both coalitions](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/debrief-mission-impact.png)

*The debrief leads with the Mission Impact summary (end-state, captures, runway damage, loss counts) before the full casualty tables.*

## See also

- [Getting Started](Getting-Started)
- [Mission Planning](Mission-planning)
- [Map Layers and Interface](Map-Layers-and-Interface)
- [414th Fork Overview](414th-Fork-Overview)
- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Home](Home)
