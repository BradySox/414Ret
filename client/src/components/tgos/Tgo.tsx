import {
  useDeleteUserPlacedTgoMutation,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
} from "../../api/liberationApi";
import { Tgo as TgoModel } from "../../api/liberationApi";
import {
  selectHighlightEmitters,
  selectHoveredEmitter,
  setHoveredEmitter,
} from "../../api/mapSlice";
import { useAppDispatch, useAppSelector } from "../../app/hooks";
import { mapColors, mapStrokes } from "../../theme/mapColors";
import { CasedCircle } from "../map/CasedShapes";
import MobileTgo from "./MobileTgo";
import { TgoTooltip, iconForTgo } from "./shared";
import { Marker, Tooltip } from "react-leaflet";
import L from "leaflet";

// The centred "?" that marks a lone suspected-activity circle as a go-look
// contact (built once — it never varies). Non-interactive so clicks fall through
// to the circle beneath it; the amber matches mapColors.suspected, haloed dark so
// it reads on light desert imagery.
const SUSPECTED_GLYPH_ICON = L.divIcon({
  className: "suspected-glyph-icon",
  html: `<span style="color:${mapColors.suspected};font-weight:700;font-size:15px;line-height:18px;text-shadow:0 0 2px #141414,0 0 2px #141414;">?</span>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

interface TgoProps {
  tgo: TgoModel;
}

/* Concealment: an un-reconned hidden enemy object — a COIN insurgent spawn
   (IED/VBIED, HVT convoy, cells) or, with concealed_enemy_forces on, any enemy
   field force (mobile SAM, deployed vehicle group, missile site) — renders as an
   "in here somewhere" uncertainty circle instead of an exact marker. The centre
   the server sends is already jittered off the true position (which never reaches
   the client while concealed). Same click/right-click contract as a marker so the
   player can frag recon (TARPS) or a strike onto the suspected area; once
   discovered the TGO snaps to its normal exact symbol. */
function ConcealedTgo(props: TgoProps) {
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  // Clustered sites (2+ concealed circles at one control point) still STACK
  // their fills into a density gradient — darker where more units hide — but
  // each member now also draws a (lighter) red-cased amber ring. A stroke-less
  // fill was invisible on satellite imagery (the flown finding: "I can hardly
  // see these zones"); the lighter cluster signature keeps several stacked
  // rings from ringing like klaxons while still bordering every circle. A lone
  // circle keeps the bolder ring plus the "?" glyph.
  const clustered = (props.tgo.concealed_cluster_size ?? 1) >= 2;
  const eventHandlers = {
    click: () => {
      openInfoDialog({ tgoId: props.tgo.id });
    },
    contextmenu: () => {
      openNewPackageDialog({ tgoId: props.tgo.id });
    },
  };
  // Amber "suspected" reads as "unknown — investigate" rather than a threat.
  const tooltip = (
    <Tooltip>
      Suspected enemy activity ({props.tgo.control_point_name})
      <br />
      Somewhere in this area — fly recon to localize
      <br />
      <i>Left-click: intel · Right-click: plan a package</i>
    </Tooltip>
  );
  if (clustered) {
    return (
      <CasedCircle
        center={props.tgo.position}
        radius={props.tgo.uncertainty_radius_m!}
        color={mapColors.suspected}
        signature={mapStrokes.suspectedCluster}
        // Kept low because the members' fills stack — 3 overlapping ≈ 0.44,
        // 6 ≈ 0.68 — the density ramp survives the added ring.
        fillOpacity={0.18}
        className="map-interactive"
        eventHandlers={eventHandlers}
      >
        {tooltip}
      </CasedCircle>
    );
  }
  return (
    <>
      <CasedCircle
        center={props.tgo.position}
        radius={props.tgo.uncertainty_radius_m!}
        color={mapColors.suspected}
        signature={mapStrokes.suspectedArea}
        // Deep enough to read as an area at a glance over satellite imagery
        // (0.18 still washed out on desert tan).
        fillOpacity={0.25}
        className="map-interactive"
        eventHandlers={eventHandlers}
      >
        {tooltip}
      </CasedCircle>
      {/* The go-look "?" at the (jittered) centre. Non-interactive so the circle
          under it keeps the click/right-click contract. Only the LONE circle gets
          one — a cluster renders the density cloud, and a field of "?"s would be
          exactly the clutter the glyph is meant to cut. */}
      <Marker
        position={props.tgo.position}
        icon={SUSPECTED_GLYPH_ICON}
        interactive={false}
        keyboard={false}
      />
    </>
  );
}

function StaticTgo(props: TgoProps) {
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();
  const [deleteTgo] = useDeleteUserPlacedTgoMutation();
  const dispatch = useAppDispatch();
  // Raised above other icons while this emitter (or its ring) is hovered.
  const raised = useAppSelector(
    (state) =>
      selectHighlightEmitters(state) &&
      selectHoveredEmitter(state) === props.tgo.id
  );
  return (
    <Marker
      position={props.tgo.position}
      icon={iconForTgo(props.tgo)}
      zIndexOffset={raised ? 10000 : 0}
      eventHandlers={{
        click: () => {
          openInfoDialog({ tgoId: props.tgo.id });
        },
        contextmenu: () => {
          if (props.tgo.user_placed) {
            deleteTgo({ tgoId: props.tgo.id });
          } else {
            openNewPackageDialog({ tgoId: props.tgo.id });
          }
        },
        // Hovering the emitter highlights its ring (and vice versa).
        mouseover: () =>
          dispatch(setHoveredEmitter({ id: props.tgo.id, source: "emitter" })),
        mouseout: () => dispatch(setHoveredEmitter(null)),
      }}
    >
      <TgoTooltip tgo={props.tgo} />
    </Marker>
  );
}

export default function Tgo(props: TgoProps) {
  if (props.tgo.uncertainty_radius_m) {
    return <ConcealedTgo tgo={props.tgo} />;
  }
  if (props.tgo.mobile) {
    return <MobileTgo tgo={props.tgo} />;
  }
  return <StaticTgo tgo={props.tgo} />;
}
