import { selectDownedPilots } from "../../api/downedPilotSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors } from "../../theme/mapColors";
import { CircleMarker, LayerGroup, Tooltip } from "react-leaflet";

// §21 downed-aviator overlay: MIA evaders (rescue orange, solid) at their last
// known position — the between-turns host plans the rescue from this marker —
// and POWs (gray, dashed) at the holding enemy field, where a recapture frees
// them. Renders nothing when nobody is down. BLUE-only: these are your own
// aviators, so nothing here is fogged.
export default function DownedPilotsLayer() {
  const pilots = useAppSelector(selectDownedPilots);
  return (
    <LayerGroup>
      {pilots.map((pilot, idx) => {
        const pow = pilot.status === "pow";
        const color = pow ? mapColors.pilotPow : mapColors.pilotMia;
        return (
          <CircleMarker
            key={`downed-pilot-${idx}`}
            center={pilot.position}
            radius={7}
            color={color}
            weight={2}
            dashArray={pow ? "2 4" : undefined}
            fill={true}
            fillColor={color}
            fillOpacity={0.35}
          >
            <Tooltip sticky>
              <b>{pow ? "POW" : "PILOT DOWN"}</b>
              <br />
              {`${pilot.name} — ${pilot.detail}`}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </LayerGroup>
  );
}
