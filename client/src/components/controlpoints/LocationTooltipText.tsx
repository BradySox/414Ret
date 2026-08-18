import SplitLines from "../splitlines/SplitLines";
import summarizeUnits from "../unitsummary/summarizeUnits";

interface LocationTooltipTextProps {
  name: string;
  tacan?: string | null;
  atcFrequency?: string | null;
  units?: string[];
  supplyStatus?: string | null;
}

// §90 rung A decides whether a base rebuilds at all. Only the states that cost
// the player something are shown -- a "SUPPLIED" line on every friendly base
// every turn is noise, and the normal case should stay quiet.
const SUPPLY_WARNINGS: { [key: string]: { text: string; color: string } } = {
  ISOLATED: { text: "Cut off — not being reinforced", color: "#c0392b" },
  AIRLIFTED: { text: "Air resupply only — rebuilding slowly", color: "#b9770e" },
};

export const LocationTooltipText = (props: LocationTooltipTextProps) => {
  const supply = props.supplyStatus
    ? SUPPLY_WARNINGS[props.supplyStatus]
    : undefined;
  return (
    <>
      <h3 style={{ margin: 0 }}>{props.name}</h3>
      {supply && (
        <div style={{ marginTop: 2, color: supply.color, fontWeight: "bold" }}>
          {supply.text}
        </div>
      )}
      {props.atcFrequency && (
        <div style={{ marginTop: 2 }}>ATC: {props.atcFrequency}</div>
      )}
      {props.tacan && <div>TACAN: {props.tacan}</div>}
      {props.units && props.units.length > 0 && (
        <SplitLines items={summarizeUnits(props.units)} />
      )}
    </>
  );
};

export default LocationTooltipText;
