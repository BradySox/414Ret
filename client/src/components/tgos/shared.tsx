import { Tgo as TgoModel } from "../../api/liberationApi";
import { mapColors } from "../../theme/mapColors";
import SplitLines from "../splitlines/SplitLines";
import summarizeUnits from "../unitsummary/summarizeUnits";
import { Icon, Point } from "leaflet";
import ms from "milsymbol";
import { Tooltip } from "react-leaflet";

export function iconForTgo(tgo: TgoModel) {
  const symbol = new ms.Symbol(tgo.sidc, { size: 24 });
  return new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(symbol.getAnchor().x, symbol.getAnchor().y),
  });
}

export function TgoTooltip(props: { tgo: TgoModel }) {
  return (
    <Tooltip>
      {`${props.tgo.name} (${props.tgo.control_point_name})`}
      {/* ROE (campaign phases W4): the target is visible but off-limits this
          phase -- you can see it, you may not hit it. Striking it anyway costs
          political will. The reason line says WHY (class lock vs sanctuary) so
          a locked factory far from any circle doesn't read as a render bug. */}
      {props.tgo.roe_restricted && (
        <>
          <br />
          <b style={{ color: mapColors.offLimits }}>RESTRICTED — ROE</b>
          {props.tgo.roe_reason && (
            <>
              <br />
              <span style={{ color: "#a34040" }}>{props.tgo.roe_reason}</span>
            </>
          )}
        </>
      )}
      <br />
      {/* Condensed: an objective's units collapse to per-type counts and cap
          out, so a FOB's hundred statics don't fill the screen on hover. */}
      <SplitLines items={summarizeUnits(props.tgo.units)} />
      <br />
      {/* Right-click DELETES a user-placed group (the drop-spawn contract) --
          advertising "plan a package" there would mislead into removing it. */}
      <i>
        {props.tgo.user_placed
          ? "Left-click: intel · Right-click: remove this placed group"
          : "Left-click: intel · Right-click: plan a package"}
      </i>
    </Tooltip>
  );
}
