import {
  FrontLine as FrontLineModel,
  useOpenNewFrontLinePackageDialogMutation,
} from "../../api/liberationApi";
import { mapColors } from "../../theme/mapColors";
import { Polyline, Tooltip } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const [openNewPackageDialog] = useOpenNewFrontLinePackageDialogMutation();
  return (
    <>
      <Polyline
        positions={props.front.extents}
        weight={16}
        color={mapColors.flot}
      />
      {/* The visible line spans only the conflict zone (~20-30 km on compressed
          campaigns) at weight 16 -- a small target. This wide, invisible hit line
          makes the front line easy to right-click for fragging. A pointer cursor +
          hover hint make the otherwise-hidden right-click discoverable.

          Layer ORDER is not what keeps this reachable. The old comment here claimed
          "the front-lines layer renders above supply routes (MapLayersControl order),
          so it already wins clicks at the FLOT" -- true against supply routes, but the
          blue/red flight layers are declared AFTER frontLines and are also DEFAULT_ON,
          and FlightPlan lays its own weight-16 invisible hit polyline with no
          contextmenu handler. Leaflet found that layer, saw no contextmenu listener,
          never fell through to this one, and the browser menu opened instead. The fix
          is the dedicated z-450 Pane in FrontLinesLayer (upstream #921) -- panes
          hit-test in z order, so declaration order stops mattering. */}
      <Polyline
        positions={props.front.extents}
        pathOptions={{ opacity: 0, weight: 28, className: "map-interactive" }}
        eventHandlers={{
          contextmenu: () => {
            openNewPackageDialog({ frontLineId: props.front.id });
          },
        }}
      >
        <Tooltip sticky>
          Front line
          <br />
          <i>Right-click: plan a mission here</i>
        </Tooltip>
      </Polyline>
    </>
  );
}

export default FrontLine;
