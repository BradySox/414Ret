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
import FlightPlansLayer from "../flightplanslayer";
import FrontLinesLayer from "../frontlineslayer";
import Iadsnetworklayer from "../iadsnetworklayer";
import SupplyRoutesLayer from "../supplyrouteslayer";
import TgosLayer from "../tgoslayer/TgosLayer";
import "./MapLayersControl.css";

// A custom, dark-themed replacement for the stock Leaflet layers control. It owns
// the visibility of every map overlay, groups them into labelled sections, offers
// one-click preset views, and remembers the player's choices across sessions. The
// "Reveal fog of war" overview is the one exception that is deliberately NOT
// persisted (it is transient server-side view state — see FogOfWarToggle).

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
  | "flightRed";

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
  // they are driven by useEffect below (see comment there), so they render no node.
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
  emitterHighlight: {
    label: "Highlight radar emitter on hover",
    node: null,
  },
  flightSelected: {
    label: "Selected flight plan",
    node: <FlightPlansLayer selectedOnly />,
  },
  flightBlue: { label: "All blue flight plans", node: <FlightPlansLayer blue={true} /> },
  flightRed: { label: "All red flight plans", node: <FlightPlansLayer blue={false} /> },
};

const ALL_IDS = Object.keys(OVERLAYS) as LayerId[];

const DEFAULT_ON: LayerId[] = [
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

const STORAGE_KEY = "fjg.mapLayers.v1";

function fromList(ids: LayerId[]): Record<LayerId, boolean> {
  const out = {} as Record<LayerId, boolean>;
  for (const id of ALL_IDS) out[id] = false;
  for (const id of ids) out[id] = true;
  return out;
}

function loadPersisted(): {
  visible?: Partial<Record<LayerId, boolean>>;
  baseMap?: BaseMap;
  bandsOpen?: boolean;
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
  const [bandsOpen, setBandsOpen] = useState<boolean>(persisted.bandsOpen ?? false);

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

  useEffect(() => {
    // Persist everything except the fog overview, which is transient view state.
    const persistable: Partial<Record<LayerId, boolean>> = { ...visible };
    delete persistable.revealFog;
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ visible: persistable, baseMap, bandsOpen })
    );
  }, [visible, baseMap, bandsOpen]);

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

  const toggle = (id: LayerId) =>
    setVisible((v) => ({ ...v, [id]: !v[id] }));
  const applyPreset = (name: string) =>
    setVisible((v) => ({ ...fromList(PRESETS[name]), revealFog: v.revealFog }));

  const baseName =
    baseMap === "firefly"
      ? "ImageryFirefly"
      : baseMap === "topo"
      ? "Topographic"
      : "ImageryClarity";

  const Row = ({
    id,
    accent,
    sub,
  }: {
    id: LayerId;
    accent?: boolean;
    sub?: boolean;
  }) => (
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

      <div className="ml-group-title">Friendly &amp; shared</div>
      <Row id="controlPoints" />
      <Row id="aircraft" />
      <Row id="combat" />
      <Row id="supplyRoutes" />
      <Row id="frontLines" />
      <Row id="factories" />
      <Row id="ships" />
      <Row id="otherGround" />

      <div className="ml-group-title">
        Air defences
        <button
          className="ml-collapse"
          aria-label={bandsOpen ? "Hide bands" : "Show bands"}
          onClick={() => setBandsOpen((b) => !b)}
        >
          {bandsOpen ? "–" : "+"}
        </button>
      </div>
      <Row id="airDefenses" />
      {bandsOpen && (
        <>
          <Row id="lorad" sub />
          <Row id="merad" sub />
          <Row id="shorad" sub />
          <Row id="aaa" sub />
        </>
      )}

      <div className="ml-group-title">Enemy intel</div>
      <Row id="revealFog" accent />
      <Row id="enemySamThreat" />
      <Row id="enemySamDetection" />
      <Row id="enemyIads" />

      <div className="ml-group-title">Allied &amp; flight plans</div>
      <Row id="alliedSamThreat" />
      <Row id="alliedSamDetection" />
      <Row id="alliedIads" />
      <Row id="emitterHighlight" />
      <Row id="flightSelected" />
      <Row id="flightBlue" />
      <Row id="flightRed" />

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
