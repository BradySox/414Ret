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
import { mapColors } from "../../theme/mapColors";
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
  return (
    <Circle
      center={props.tgo.position}
      radius={props.tgo.uncertainty_radius_m!}
      // Amber "suspected", not red: red is reserved for the ROE off-limits circle,
      // which is nearly identical in shape. Amber reads as "unknown — investigate".
      pathOptions={{
        color: mapColors.suspected,
        weight: 2,
        dashArray: "6 6",
        fillColor: mapColors.suspected,
        fillOpacity: 0.08,
        className: "map-interactive",
      }}
      eventHandlers={{
        click: () => {
          openInfoDialog({ tgoId: props.tgo.id });
        },
        contextmenu: () => {
          openNewPackageDialog({ tgoId: props.tgo.id });
        },
      }}
    >
      <Tooltip>
        Suspected enemy activity ({props.tgo.control_point_name})
        <br />
        Somewhere in this area — fly recon to localize
        <br />
        <i>Left-click: intel · Right-click: plan a package</i>
      </Tooltip>
    </Circle>
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
