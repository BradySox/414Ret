import { selectDownedPilots } from "../../api/downedPilotSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors, mapStrokes } from "../../theme/mapColors";
import { CasedCircleMarker } from "../map/CasedShapes";
import { LayerGroup, Tooltip } from "react-leaflet";

// §21 downed-aviator overlay: MIA evaders (rescue orange, solid) at their last
// known position — the between-turns host plans the rescue from this marker —
// and POWs (gray, short-dashed) at the holding enemy field, where a recapture
// frees them. Both cased so the small markers read over any imagery. Renders
// nothing when nobody is down. BLUE-only: these are your own aviators, so
// nothing here is fogged.
export default function DownedPilotsLayer() {
  const pilots = useAppSelector(selectDownedPilots);
  return (
    <LayerGroup>
      {pilots.map((pilot, idx) => {
        const pow = pilot.status === "pow";
        return (
          <CasedCircleMarker
            key={`downed-pilot-${idx}`}
            center={pilot.position}
            radius={7}
            color={pow ? mapColors.pilotPow : mapColors.pilotMia}
            signature={pow ? mapStrokes.pilotPow : mapStrokes.pilotMia}
            fillOpacity={0.35}
          >
            <Tooltip sticky>
              <b>{pow ? "POW" : "PILOT DOWN"}</b>
              <br />
              {`${pilot.name} — ${pilot.detail}`}
            </Tooltip>
          </CasedCircleMarker>
        );
      })}
    </LayerGroup>
  );
}
