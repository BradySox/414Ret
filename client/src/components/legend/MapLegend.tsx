import { mapColors } from "../../theme/mapColors";
import "./MapLegend.css";
import { CSSProperties, useState } from "react";

// A compact, collapsible key for the map's colour/shape semantics. The many overlays
// reuse a small set of meanings (allegiance, ROE, supply, suspected activity) that
// aren't otherwise decodable -- especially the two dashed circles (amber = suspected
// enemy to scout; red = ROE off-limits) that used to look alike. Floats bottom-right
// so it clears the ruler (top-left), layers panel (top-right), campaign ribbon
// (top-centre), and the events feed + scale bar (bottom-left). Collapsed by default.

type SwatchKind = "fill" | "line" | "dashed";

function Swatch(props: { color: string; kind: SwatchKind }) {
  const base = { "--legend-swatch": props.color } as CSSProperties;
  return <span className={`legend-swatch legend-swatch-${props.kind}`} style={base} />;
}

interface Row {
  color: string;
  kind: SwatchKind;
  label: string;
}

const ROWS: Row[] = [
  { color: mapColors.friendly, kind: "line", label: "Friendly (forces, threat rings)" },
  { color: mapColors.enemy, kind: "line", label: "Enemy (forces, threat rings)" },
  {
    color: mapColors.detectionFriendly,
    kind: "line",
    label: "Radar detection ring: friendly",
  },
  {
    color: mapColors.detectionEnemy,
    kind: "line",
    label: "Radar detection ring: enemy",
  },
  { color: mapColors.flot, kind: "line", label: "Front line (FLOT)" },
  { color: mapColors.suspected, kind: "dashed", label: "Suspected activity — scout it" },
  { color: mapColors.offLimits, kind: "dashed", label: "ROE off-limits — no strike" },
  { color: mapColors.weaponsFree, kind: "dashed", label: "Weapons-free pocket" },
  { color: mapColors.pilotMia, kind: "fill", label: "Pilot down — evading, fly the rescue" },
  { color: mapColors.pilotPow, kind: "dashed", label: "POW — held at an enemy field" },
  { color: mapColors.mine, kind: "dashed", label: "Minefield (your own)" },
  { color: mapColors.supplyOk, kind: "fill", label: "Supply: healthy" },
  { color: mapColors.supplyMid, kind: "fill", label: "Supply: strained" },
  { color: mapColors.supplyLow, kind: "fill", label: "Supply: low" },
  { color: mapColors.supplyCritical, kind: "fill", label: "Supply: starved" },
  { color: mapColors.supplyProducer, kind: "line", label: "Supply producer (factory/oil)" },
  { color: mapColors.routeFriendly, kind: "line", label: "Convoy route: friendly" },
  { color: mapColors.routeEnemy, kind: "line", label: "Convoy route: enemy — interdict" },
  { color: mapColors.routeContested, kind: "line", label: "Convoy route: contested" },
];

export default function MapLegend() {
  const [open, setOpen] = useState(false);
  return (
    <div className="map-legend">
      <button
        type="button"
        className="map-legend-toggle"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? "▾ " : "▸ "}Legend
      </button>
      {open && (
        <div className="map-legend-body">
          {ROWS.map((row) => (
            <div className="map-legend-row" key={row.label}>
              <Swatch color={row.color} kind={row.kind} />
              <span className="map-legend-label">{row.label}</span>
            </div>
          ))}
          <div className="map-legend-hint">
            Left-click a target for intel · right-click to plan a package
          </div>
        </div>
      )}
    </div>
  );
}
