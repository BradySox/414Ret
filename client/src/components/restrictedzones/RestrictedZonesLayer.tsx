import { selectRestrictedZones } from "../../api/restrictedZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { Circle, LayerGroup, Tooltip } from "react-leaflet";

// ROE restricted zones (campaign phases W4): red dashed circles where the
// current phase forbids offensive tasking (Route-Package sanctuaries). Drawn
// like threat rings but dashed so they read as *rules*, not radar coverage.
// Renders nothing outside authored ROE campaigns (the zones list is empty).
export default function RestrictedZonesLayer() {
  const zones = useAppSelector(selectRestrictedZones);
  return (
    <LayerGroup>
      {zones.map((zone, idx) => (
        <Circle
          key={`${zone.name}-${idx}`}
          center={zone.center}
          radius={zone.radius_m}
          color="#d43a3a"
          weight={2}
          dashArray="10 10"
          fill
          fillColor="#d43a3a"
          fillOpacity={0.06}
          interactive
        >
          <Tooltip sticky>{`${zone.name} — RESTRICTED (ROE)`}</Tooltip>
        </Circle>
      ))}
    </LayerGroup>
  );
}
