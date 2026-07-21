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
import { Circle, Marker, Tooltip } from "react-leaflet";

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
  // Clustered sites (2+ concealed circles at one control point) render as a
  // DENSITY CLOUD: no per-circle stroke (nine stacked dashed rings rang like
  // klaxons on the flown Red Tide map) and a low fill that STACKS where the
  // circles overlap — darker exactly where more units hide, while the union
  // of the members' own circles covers the area they actually hold. A lone
  // circle keeps the classic dashed "suspected activity" ring — cased, so it
  // reads on desert imagery (the flown Iraq map washed bare amber out).
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
      <Circle
        center={props.tgo.position}
        radius={props.tgo.uncertainty_radius_m!}
        pathOptions={{
          stroke: false,
          fillColor: mapColors.suspected,
          // Low, because the members' fills stack — 3 overlapping ≈ 0.41,
          // 6 ≈ 0.65, 9 ≈ 0.79 — the density ramp.
          fillOpacity: 0.16,
          className: "map-interactive",
        }}
        eventHandlers={eventHandlers}
      >
        {tooltip}
      </Circle>
    );
  }
  return (
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
