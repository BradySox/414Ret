import { RestrictedZone } from "../../api/liberationApi";
import {
  selectFreeFireZones,
  selectRestrictedZones,
} from "../../api/restrictedZonesSlice";
import { useAppSelector } from "../../app/hooks";
import { StrokeSignature, mapColors, mapStrokes } from "../../theme/mapColors";
import { CasedCircle, CasedPolygon } from "../map/CasedShapes";
import { LayerGroup, Tooltip } from "react-leaflet";

// Restricted (no-strike) zones are red; free-fire (weapons-free) pockets are green —
// the opposite reading of the same shape system (inverted ROE, COIN). The suspected-
// enemy (concealed) circle is deliberately amber, not red, so it can't be confused
// with an off-limits circle here. Beyond colour, each carries its own stroke
// signature (long dash = authored ROE border; the dash-dot variant = weapons free;
// the suspected area's medium dash stays distinct), all drawn over a dark contrast
// casing so the borders read on light desert imagery as well as dark terrain.
const RESTRICTED_COLOR = mapColors.offLimits;
const FREE_FIRE_COLOR = mapColors.weaponsFree;

// Shade the area clearly enough to read as a region over satellite imagery —
// a faint 6% fill left large box/corridor zones looking like a lone dashed edge.
const ZONE_FILL_OPACITY = 0.14;

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
  signature: StrokeSignature;
  label: string;
  keyPrefix: string;
}) {
  return (
    <>
      {props.zones.map((zone, idx) =>
        zone.kind === "circle" || zone.outline.length < 3 ? (
          <CasedCircle
            key={`${props.keyPrefix}-${zone.name}-${idx}`}
            center={zone.center}
            radius={zone.radius_m}
            color={props.color}
            signature={props.signature}
            fillOpacity={ZONE_FILL_OPACITY}
          >
            <ZoneTooltip zone={zone} label={props.label} />
          </CasedCircle>
        ) : (
          <CasedPolygon
            key={`${props.keyPrefix}-${zone.name}-${idx}`}
            positions={zone.outline}
            color={props.color}
            signature={props.signature}
            fillOpacity={ZONE_FILL_OPACITY}
          >
            <ZoneTooltip zone={zone} label={props.label} />
          </CasedPolygon>
        )
      )}
    </>
  );
}

// ROE zones (campaign phases W4): red long-dashed **restricted** (no-strike) shapes,
// and green dash-dot **free-fire** (weapons-free) pockets for inverted ROE (COIN). A
// circle draws from center/radius; a box/corridor/polygon from its outline. Dashed so
// they read as *rules*, not radar coverage. Renders nothing outside authored ROE
// campaigns (both lists empty). Free-fire drawn first so a red no-strike carve-out
// sits on top.
export default function RestrictedZonesLayer() {
  const restricted = useAppSelector(selectRestrictedZones);
  const freeFire = useAppSelector(selectFreeFireZones);
  return (
    <LayerGroup>
      <ZoneShapes
        zones={freeFire}
        color={FREE_FIRE_COLOR}
        signature={mapStrokes.weaponsFree}
        label="WEAPONS FREE (ROE)"
        keyPrefix="ff"
      />
      <ZoneShapes
        zones={restricted}
        color={RESTRICTED_COLOR}
        signature={mapStrokes.roeRestricted}
        label="RESTRICTED (ROE)"
        keyPrefix="rz"
      />
    </LayerGroup>
  );
}
