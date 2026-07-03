import { RestrictedZone } from "../../api/liberationApi";
import { selectRestrictedZones } from "../../api/restrictedZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { Circle, LayerGroup, Polygon, Tooltip } from "react-leaflet";

const ZONE_STYLE = {
  color: "#d43a3a",
  weight: 2,
  dashArray: "10 10",
  fill: true,
  fillColor: "#d43a3a",
  fillOpacity: 0.06,
  interactive: true,
} as const;

function ZoneTooltip(props: { zone: RestrictedZone }) {
  return (
    <Tooltip sticky>
      <b>{`${props.zone.name} — RESTRICTED (ROE)`}</b>
      {props.zone.detail && (
        <>
          <br />
          {props.zone.detail}
        </>
      )}
    </Tooltip>
  );
}

// ROE restricted zones (campaign phases W4): red dashed shapes where the current
// phase forbids offensive tasking (Route-Package sanctuaries). A circle is drawn
// from center/radius; a box or corridor from its polygon outline. Dashed so they
// read as *rules*, not radar coverage. Renders nothing outside authored ROE
// campaigns (the zones list is empty).
export default function RestrictedZonesLayer() {
  const zones = useAppSelector(selectRestrictedZones);
  return (
    <LayerGroup>
      {zones.map((zone, idx) =>
        zone.kind === "circle" || zone.outline.length < 3 ? (
          <Circle
            key={`${zone.name}-${idx}`}
            center={zone.center}
            radius={zone.radius_m}
            {...ZONE_STYLE}
          >
            <ZoneTooltip zone={zone} />
          </Circle>
        ) : (
          <Polygon
            key={`${zone.name}-${idx}`}
            positions={zone.outline}
            {...ZONE_STYLE}
          >
            <ZoneTooltip zone={zone} />
          </Polygon>
        )
      )}
    </LayerGroup>
  );
}
