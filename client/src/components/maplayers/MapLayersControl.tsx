import { Fragment, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useMap } from "react-leaflet";
import { BasemapLayer } from "react-esri-leaflet";
import L from "leaflet";

import backend from "../../api/backend";
import reloadGameState from "../../api/gamestate";
import { setHighlightEmitters } from "../../api/mapSlice";
import { useAppDispatch } from "../../app/hooks";
import AircraftLayer from "../aircraftlayer";
import AirDefenseRangeLayer from "../airdefenserangelayer";
import CombatLayer from "../combatlayer";
import ControlPointsLayer from "../controlpointslayer";
import {
  CullingExclusionLayer,
} from "../cullingexclusionzones/CullingExclusionZones";
import FlightPlansLayer from "../flightplanslayer";
import FrontLinesLayer from "../frontlineslayer";
import Iadsnetworklayer from "../iadsnetworklayer";
import NavMeshLayer from "../navmesh/NavMeshLayer";
import RestrictedZonesLayer from "../restrictedzones";
import SupplyRoutesLayer from "../supplyrouteslayer";
import {
  ExclusionZonesLayer,
  InclusionZonesLayer,
  SeaZonesLayer,
} from "../terrainzones/TerrainZonesLayers";
import { ThreatZoneFilter, ThreatZonesLayer } from "../threatzones";
import TgosLayer from "../tgoslayer/TgosLayer";
import "./MapLayersControl.css";

// A custom, dark-themed replacement for the two stock Leaflet layer controls.
// Everything lives in one collapsible, grouped panel: common layers up top,
// advanced/debug overlays (threat zones, navmesh, terrain) tucked into groups
// that start collapsed so the list stays short. Choices are persisted into the
// campaign save (with a localStorage cache), EXCEPT the fog overview, which is
// transient server-side view state.

type LayerId =
  | "controlPoints"
  | "aircraft"
  | "combat"
  | "supplyRoutes"
  | "frontLines"
  | "factories"
  | "ships"
  | "otherGround"
  | "airDefenses"
  | "lorad"
  | "merad"
  | "shorad"
  | "aaa"
  | "revealFog"
  | "enemySamThreat"
  | "enemySamDetection"
  | "enemyIads"
  | "alliedSamThreat"
  | "alliedSamDetection"
  | "alliedIads"
  | "emitterHighlight"
  | "flightSelected"
  | "flightBlue"
  | "flightRed"
  | "blueThreatFull"
  | "blueThreatAircraft"
  | "blueThreatAirDef"
  | "blueThreatRadar"
  | "redThreatFull"
  | "redThreatAircraft"
  | "redThreatAirDef"
  | "redThreatRadar"
  | "blueNavmesh"
  | "redNavmesh"
  | "inclusionZones"
  | "exclusionZones"
  | "seaZones"
  | "cullingZones"
  | "restrictedZones";

type BaseMap = "clarity" | "firefly" | "topo";

const OVERLAYS: Record<LayerId, { label: string; node: ReactNode }> = {
  controlPoints: { label: "Control points", node: <ControlPointsLayer /> },
  aircraft: { label: "Aircraft", node: <AircraftLayer /> },
  combat: { label: "Active combat", node: <CombatLayer /> },
  supplyRoutes: { label: "Supply routes", node: <SupplyRoutesLayer /> },
  frontLines: { label: "Front lines", node: <FrontLinesLayer /> },
  factories: { label: "Factories", node: <TgosLayer categories={["factory"]} /> },
  ships: { label: "Ships", node: <TgosLayer categories={["ship"]} /> },
  otherGround: {
    label: "Other ground objects",
    node: <TgosLayer categories={["aa", "factory", "ship"]} exclude />,
  },
  airDefenses: { label: "Air defences", node: <TgosLayer categories={["aa"]} /> },
  lorad: { label: "LORAD", node: <TgosLayer categories={["aa"]} task={"LORAD"} /> },
  merad: { label: "MERAD", node: <TgosLayer categories={["aa"]} task={"MERAD"} /> },
  shorad: { label: "SHORAD", node: <TgosLayer categories={["aa"]} task={"SHORAD"} /> },
  aaa: { label: "AAA", node: <TgosLayer categories={["aa"]} task={"AAA"} /> },
  // revealFog and emitterHighlight are side-effect toggles, not visual layers:
  // they are driven by useEffect below, so they render no node.
  revealFog: { label: "Reveal fog of war", node: null },
  enemySamThreat: {
    label: "Enemy SAM threat range",
    node: <AirDefenseRangeLayer blue={false} />,
  },
  enemySamDetection: {
    label: "Enemy SAM detection range",
    node: <AirDefenseRangeLayer blue={false} detection />,
  },
  enemyIads: { label: "Enemy IADS network", node: <Iadsnetworklayer blue={false} /> },
  alliedSamThreat: {
    label: "Allied SAM threat range",
    node: <AirDefenseRangeLayer blue={true} />,
  },
  alliedSamDetection: {
    label: "Allied SAM detection range",
    node: <AirDefenseRangeLayer blue={true} detection />,
  },
  alliedIads: { label: "Allied IADS network", node: <Iadsnetworklayer blue={true} /> },
  emitterHighlight: { label: "Highlight radar emitter on hover", node: null },
  flightSelected: {
    label: "Selected flight plan",
    node: <FlightPlansLayer selectedOnly />,
  },
  flightBlue: { label: "All blue flight plans", node: <FlightPlansLayer blue={true} /> },
  flightRed: { label: "All red flight plans", node: <FlightPlansLayer blue={false} /> },
  blueThreatFull: {
    label: "Blue: full",
    node: <ThreatZonesLayer blue={true} filter={ThreatZoneFilter.FULL} />,
  },
  blueThreatAircraft: {
    label: "Blue: aircraft",
    node: <ThreatZonesLayer blue={true} filter={ThreatZoneFilter.AIRCRAFT} />,
  },
  blueThreatAirDef: {
    label: "Blue: air defences",
    node: <ThreatZonesLayer blue={true} filter={ThreatZoneFilter.AIR_DEFENSES} />,
  },
  blueThreatRadar: {
    label: "Blue: radar SAMs",
    node: <ThreatZonesLayer blue={true} filter={ThreatZoneFilter.RADAR_SAMS} />,
  },
  redThreatFull: {
    label: "Red: full",
    node: <ThreatZonesLayer blue={false} filter={ThreatZoneFilter.FULL} />,
  },
  redThreatAircraft: {
    label: "Red: aircraft",
    node: <ThreatZonesLayer blue={false} filter={ThreatZoneFilter.AIRCRAFT} />,
  },
  redThreatAirDef: {
    label: "Red: air defences",
    node: <ThreatZonesLayer blue={false} filter={ThreatZoneFilter.AIR_DEFENSES} />,
  },
  redThreatRadar: {
    label: "Red: radar SAMs",
    node: <ThreatZonesLayer blue={false} filter={ThreatZoneFilter.RADAR_SAMS} />,
  },
  blueNavmesh: { label: "Blue navmesh", node: <NavMeshLayer blue={true} /> },
  redNavmesh: { label: "Red navmesh", node: <NavMeshLayer blue={false} /> },
  inclusionZones: { label: "Inclusion zones", node: <InclusionZonesLayer /> },
  exclusionZones: { label: "Exclusion zones", node: <ExclusionZonesLayer /> },
  seaZones: { label: "Sea zones", node: <SeaZonesLayer /> },
  cullingZones: { label: "Culling exclusion zones", node: <CullingExclusionLayer /> },
  // ROE restricted zones (campaign phases W4). Only authored ROE campaigns emit
  // zones, so the layer is a no-op everywhere else even while toggled on.
  restrictedZones: {
    label: "ROE restricted zones",
    node: <RestrictedZonesLayer />,
  },
};

const ALL_IDS = Object.keys(OVERLAYS) as LayerId[];

interface RowDef {
  id: LayerId;
  accent?: boolean;
  sub?: boolean;
}

interface GroupDef {
  key: string;
  title: string;
  defaultOpen: boolean;
  rows: RowDef[];
}

const GROUPS: GroupDef[] = [
  {
    key: "friendly",
    title: "Friendly & shared",
    defaultOpen: true,
    rows: [
      { id: "controlPoints" },
      { id: "aircraft" },
      { id: "combat" },
      { id: "supplyRoutes" },
      { id: "frontLines" },
      { id: "factories" },
      { id: "ships" },
      { id: "otherGround" },
    ],
  },
  {
    key: "airdef",
    title: "Air defences",
    defaultOpen: true,
    rows: [
      { id: "airDefenses" },
      { id: "lorad", sub: true },
      { id: "merad", sub: true },
      { id: "shorad", sub: true },
      { id: "aaa", sub: true },
    ],
  },
  {
    key: "enemy",
    title: "Enemy intel",
    defaultOpen: true,
    rows: [
      { id: "revealFog", accent: true },
      { id: "enemySamThreat" },
      { id: "enemySamDetection" },
      { id: "enemyIads" },
      { id: "restrictedZones" },
    ],
  },
  {
    key: "allied",
    title: "Allied & flight plans",
    defaultOpen: false,
    rows: [
      { id: "alliedSamThreat" },
      { id: "alliedSamDetection" },
      { id: "alliedIads" },
      { id: "emitterHighlight" },
      { id: "flightSelected" },
      { id: "flightBlue" },
      { id: "flightRed" },
    ],
  },
  {
    key: "threat",
    title: "Threat zones",
    defaultOpen: false,
    rows: [
      { id: "blueThreatFull" },
      { id: "blueThreatAircraft" },
      { id: "blueThreatAirDef" },
      { id: "blueThreatRadar" },
      { id: "redThreatFull" },
      { id: "redThreatAircraft" },
      { id: "redThreatAirDef" },
      { id: "redThreatRadar" },
    ],
  },
  {
    key: "debug",
    title: "Navmesh & terrain",
    defaultOpen: false,
    rows: [
      { id: "blueNavmesh" },
      { id: "redNavmesh" },
      { id: "inclusionZones" },
      { id: "exclusionZones" },
      { id: "seaZones" },
      { id: "cullingZones" },
    ],
  },
];

const DEFAULT_ON: LayerId[] = [
  "restrictedZones",
  "controlPoints",
  "aircraft",
  "combat",
  "airDefenses",
  "factories",
  "ships",
  "otherGround",
  "supplyRoutes",
  "frontLines",
  "enemySamThreat",
  "emitterHighlight",
  "flightBlue",
];

// Presets list only the layers they switch ON; everything else goes off. The fog
// overview is left at its current state by presets (never force-revealed).
const PRESETS: Record<string, LayerId[]> = {
  Default: DEFAULT_ON,
  SEAD: [
    "controlPoints",
    "frontLines",
    "airDefenses",
    "enemySamThreat",
    "enemySamDetection",
    "enemyIads",
    "flightBlue",
  ],
  Recon: [
    "controlPoints",
    "frontLines",
    "airDefenses",
    "factories",
    "ships",
    "otherGround",
    "enemySamThreat",
  ],
  Clean: ["controlPoints", "frontLines"],
};

const STORAGE_KEY = "fjg.mapLayers.v2";

function fromList(ids: LayerId[]): Record<LayerId, boolean> {
  const out = {} as Record<LayerId, boolean>;
  for (const id of ALL_IDS) out[id] = false;
  for (const id of ids) out[id] = true;
  return out;
}

function defaultGroups(): Record<string, boolean> {
  const out: Record<string, boolean> = {};
  for (const g of GROUPS) out[g.key] = g.defaultOpen;
  return out;
}

function loadPersisted(): {
  visible?: Partial<Record<LayerId, boolean>>;
  baseMap?: BaseMap;
  openGroups?: Record<string, boolean>;
} {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

export default function MapLayersControl() {
  const map = useMap();
  const dispatch = useAppDispatch();
  const [portalEl, setPortalEl] = useState<HTMLElement | null>(null);

  const persisted = useMemo(loadPersisted, []);
  const [visible, setVisible] = useState<Record<LayerId, boolean>>(() => ({
    ...fromList(DEFAULT_ON),
    ...(persisted.visible ?? {}),
    revealFog: false, // transient: never restored from storage
  }));
  const [baseMap, setBaseMap] = useState<BaseMap>(persisted.baseMap ?? "clarity");
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => ({
    ...defaultGroups(),
    ...(persisted.openGroups ?? {}),
  }));
  // Becomes true once the saved state has been pulled from the campaign (or the
  // fetch failed); gates the write-back so the default seed can't clobber it.
  const loadedRef = useRef(false);

  useEffect(() => {
    const control = new L.Control({ position: "topright" });
    const el = L.DomUtil.create("div");
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
    control.onAdd = () => el;
    control.addTo(map);
    setPortalEl(el);
    return () => {
      control.remove();
    };
  }, [map]);

  // On mount, pull the map-layer state out of the campaign save. It travels with
  // the .retribution file, unlike localStorage, which QtWebEngine drops on reload
  // (so the panel forgot its layers after every turn). The save wins over the
  // localStorage seed when present.
  useEffect(() => {
    let cancelled = false;
    backend
      .get("/game/map-layers")
      .then((res) => {
        if (cancelled) return;
        const raw: string | null | undefined = res.data?.state;
        if (!raw) return;
        const saved = JSON.parse(raw) as {
          visible?: Partial<Record<LayerId, boolean>>;
          baseMap?: BaseMap;
          openGroups?: Record<string, boolean>;
        };
        // revealFog is transient and never written to the blob, so it stays off.
        if (saved.visible) setVisible((v) => ({ ...v, ...saved.visible }));
        if (saved.baseMap) setBaseMap(saved.baseMap);
        if (saved.openGroups) setOpenGroups((g) => ({ ...g, ...saved.openGroups }));
      })
      .catch(() => {
        // No game loaded yet or backend offline: keep the localStorage seed.
      })
      .finally(() => {
        if (!cancelled) loadedRef.current = true;
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    // Persist everything except the fog overview, which is transient view state.
    const persistable: Partial<Record<LayerId, boolean>> = { ...visible };
    delete persistable.revealFog;
    const payload = JSON.stringify({ visible: persistable, baseMap, openGroups });
    localStorage.setItem(STORAGE_KEY, payload);
    // Also persist into the campaign save (debounced) so the choices survive turns
    // and reopening the app, not just same-origin localStorage. Don't write back
    // until we've loaded it, or the default seed would clobber the stored state in
    // the window before the GET resolves.
    if (!loadedRef.current) return;
    const id = setTimeout(() => {
      backend.put("/game/map-layers", { state: payload }).catch(() => {});
    }, 500);
    return () => clearTimeout(id);
  }, [visible, baseMap, openGroups]);

  // Radar-emitter highlight is a pure client flag; keep the slice in sync with
  // the checkbox (the initial dispatch matches the default, so it is harmless).
  useEffect(() => {
    dispatch(setHighlightEmitters(visible.emitterHighlight));
  }, [dispatch, visible.emitterHighlight]);

  // Fog-of-war overview: flip the server flag and re-pull /game so the map
  // re-fogs/un-fogs. Driven by state (not layer add/remove) so unchecking
  // reliably turns it back OFF. Skip the initial mount: the flag already starts
  // off and the game has just loaded, so a reload there would be redundant.
  const fogReady = useRef(false);
  useEffect(() => {
    if (!fogReady.current) {
      fogReady.current = true;
      return;
    }
    backend
      .put("/fog-of-war/reveal", null, { params: { revealed: visible.revealFog } })
      .then(() => reloadGameState(dispatch, true))
      .catch((error) => console.log(`Error toggling fog of war: ${error}`));
  }, [dispatch, visible.revealFog]);

  const toggle = (id: LayerId) => setVisible((v) => ({ ...v, [id]: !v[id] }));
  const applyPreset = (name: string) =>
    setVisible((v) => ({ ...fromList(PRESETS[name]), revealFog: v.revealFog }));
  const toggleGroup = (key: string) =>
    setOpenGroups((g) => ({ ...g, [key]: !g[key] }));

  const baseName =
    baseMap === "firefly"
      ? "ImageryFirefly"
      : baseMap === "topo"
      ? "Topographic"
      : "ImageryClarity";

  const Row = ({ id, accent, sub }: RowDef) => (
    <label
      className={
        "ml-row" + (accent ? " ml-row-accent" : "") + (sub ? " ml-row-sub" : "")
      }
    >
      <input type="checkbox" checked={!!visible[id]} onChange={() => toggle(id)} />
      <span>{OVERLAYS[id].label}</span>
      {accent && <span className="ml-badge">overview</span>}
    </label>
  );

  const panel = (
    <div className="ml-panel">
      <div className="ml-header">Map layers</div>

      <div className="ml-presets">
        {Object.keys(PRESETS).map((name) => (
          <button key={name} className="ml-chip" onClick={() => applyPreset(name)}>
            {name}
          </button>
        ))}
      </div>

      <div className="ml-seg">
        {(
          [
            ["clarity", "Clarity"],
            ["firefly", "Firefly"],
            ["topo", "Topographic"],
          ] as [BaseMap, string][]
        ).map(([k, label]) => (
          <button
            key={k}
            className={"ml-seg-btn" + (baseMap === k ? " active" : "")}
            onClick={() => setBaseMap(k)}
          >
            {label}
          </button>
        ))}
      </div>

      {GROUPS.map((g) => (
        <Fragment key={g.key}>
          <button className="ml-group-title" onClick={() => toggleGroup(g.key)}>
            <span>{g.title}</span>
            <span className="ml-group-chevron">{openGroups[g.key] ? "−" : "+"}</span>
          </button>
          {openGroups[g.key] &&
            g.rows.map((r) => (
              <Row key={r.id} id={r.id} accent={r.accent} sub={r.sub} />
            ))}
        </Fragment>
      ))}

      <div className="ml-foot">
        <button onClick={() => applyPreset("Clean")}>Hide all overlays</button>
      </div>
    </div>
  );

  return (
    <>
      <BasemapLayer key={baseName} name={baseName} />
      {ALL_IDS.map((id) =>
        visible[id] ? <Fragment key={id}>{OVERLAYS[id].node}</Fragment> : null
      )}
      {portalEl && createPortal(panel, portalEl)}
    </>
  );
}
