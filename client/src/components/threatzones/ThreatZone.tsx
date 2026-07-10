import { LatLng } from "../../api/liberationApi";
import { mapColors } from "../../theme/mapColors";
import { Polygon } from "react-leaflet";

interface ThreatZoneProps {
  poly: LatLng[][];
  blue: boolean;
}

export default function ThreatZone(props: ThreatZoneProps) {
  const color = props.blue ? mapColors.friendly : mapColors.enemy;
  return (
    <Polygon
      positions={props.poly}
      color={color}
      weight={1}
      fill
      fillOpacity={0.4}
      noClip
      interactive={false}
    />
  );
}
