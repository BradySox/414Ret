import { RestrictedZone } from "../../api/liberationApi";
import {
  selectFreeFireZones,
  selectRestrictedZones,
} from "../../api/restrictedZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { Circle, LayerGroup, Polygon, Tooltip } from "react-leaflet";

// Restricted (no-strike) zones are red; free-fire (weapons-free) pockets are green —
// the opposite reading of the same shape system (inverted ROE, COIN).
const RESTRICTED_COLOR = "#d43a3a";
const FREE_FIRE_COLOR = "#3ccd5f";

function zoneStyle(color: string) {
  return {
    color,
    weight: 2,
    dashArray: "10 10",
    fill: true,
    fillColor: color,
    // Shade the area clearly enough to read as a region over satellite imagery --
    // a faint 6% fill left large box/corridor zones looking like a lone dashed edge.
    fillOpacity: 0.14,
    interactive: true,
  } as const;
}

function ZoneTooltip(props: { zone: RestrictedZone; label: string }) {
  return (
    <Tooltip sticky>
      <b>{`${props.zone.name} — ${props.label}`}</b>
      {props.zone.detail && (
        <>
          <br />
          {props.zone.detail}
        </>
      )}
    </Tooltip>
  );
}

function ZoneShapes(props: {
  zones: RestrictedZone[];
  color: string;
  label: string;
  keyPrefix: string;
}) {
  const style = zoneStyle(props.color);
  return (
    <>
      {props.zones.map((zone, idx) =>
        zone.kind === "circle" || zone.outline.length < 3 ? (
          <Circle
            key={`${props.keyPrefix}-${zone.name}-${idx}`}
            center={zone.center}
            radius={zone.radius_m}
            {...style}
          >
            <ZoneTooltip zone={zone} label={props.label} />
          </Circle>
        ) : (
          <Polygon
            key={`${props.keyPrefix}-${zone.name}-${idx}`}
            positions={zone.outline}
            {...style}
          >
            <ZoneTooltip zone={zone} label={props.label} />
          </Polygon>
        )
      )}
    </>
  );
}

// ROE zones (campaign phases W4): red dashed **restricted** (no-strike) shapes, and
// green dashed **free-fire** (weapons-free) pockets for inverted ROE (COIN). A circle
// draws from center/radius; a box/corridor/polygon from its outline. Dashed so they
// read as *rules*, not radar coverage. Renders nothing outside authored ROE campaigns
// (both lists empty). Free-fire drawn first so a red no-strike carve-out sits on top.
export default function RestrictedZonesLayer() {
  const restricted = useAppSelector(selectRestrictedZones);
  const freeFire = useAppSelector(selectFreeFireZones);
  return (
    <LayerGroup>
      <ZoneShapes
        zones={freeFire}
        color={FREE_FIRE_COLOR}
        label="WEAPONS FREE (ROE)"
        keyPrefix="ff"
      />
      <ZoneShapes
        zones={restricted}
        color={RESTRICTED_COLOR}
        label="RESTRICTED (ROE)"
        keyPrefix="rz"
      />
    </LayerGroup>
  );
}
