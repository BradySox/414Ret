import { StrokeSignature, mapColors, mapStrokes } from "../../theme/mapColors";
import "./MapLegend.css";
import { CSSProperties, useState } from "react";

// A compact, collapsible key for the map's colour/shape semantics. The many overlays
// reuse a small set of meanings (allegiance, supply, suspected activity) that
// aren't otherwise decodable. The dashed family renders its REAL stroke signature
// (mapStrokes: pattern + dark contrast casing) as a mini SVG preview, so the legend
// swatch is literally what the map draws — an area, a zone, a hazard, and a person
// each read differently even for a colour-blind pilot. Floats bottom-right so it
// clears the ruler (top-left), layers panel (top-right), campaign ribbon
// (top-centre), and the events feed + scale bar (bottom-left). Collapsed by default.

type SwatchKind = "fill" | "line";

function Swatch(props: { color: string; kind: SwatchKind }) {
  const base = { "--legend-swatch": props.color } as CSSProperties;
  return <span className={`legend-swatch legend-swatch-${props.kind}`} style={base} />;
}

// The on-map cased stroke in miniature: the dark casing line under the coloured
// dash, true dashArray, capped casing weight so the 12px-tall swatch stays a line.
function StrokeSwatch(props: { color: string; signature: StrokeSignature }) {
  const width = 40;
  const y = 6;
  return (
    <svg
      className="legend-swatch legend-swatch-stroke"
      width={width}
      height={12}
      viewBox={`0 0 ${width} 12`}
      aria-hidden="true"
    >
      <line
        x1={1}
        y1={y}
        x2={width - 1}
        y2={y}
        stroke={mapColors.strokeCasing}
        strokeWidth={Math.min(props.signature.casingWeight, 8)}
        strokeOpacity={0.75}
        strokeDasharray={props.signature.dashArray}
        strokeLinecap={props.signature.lineCap}
      />
      <line
        x1={1}
        y1={y}
        x2={width - 1}
        y2={y}
        stroke={props.color}
        strokeWidth={props.signature.weight}
        strokeDasharray={props.signature.dashArray}
        strokeLinecap={props.signature.lineCap}
      />
    </svg>
  );
}

type Row =
  | { color: string; kind: SwatchKind; label: string }
  | { color: string; signature: StrokeSignature; label: string };

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
  {
    color: mapColors.suspected,
    signature: mapStrokes.suspectedArea,
    label: "Suspected area — scout it",
  },
  {
    color: mapColors.pilotMia,
    signature: mapStrokes.pilotMia,
    label: "Pilot down — evading, fly the rescue",
  },
  {
    color: mapColors.pilotPow,
    signature: mapStrokes.pilotPow,
    label: "POW — held at an enemy field",
  },
  {
    color: mapColors.mine,
    signature: mapStrokes.minefield,
    label: "Minefield (your own)",
  },
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
              {"signature" in row ? (
                <StrokeSwatch color={row.color} signature={row.signature} />
              ) : (
                <Swatch color={row.color} kind={row.kind} />
              )}
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
