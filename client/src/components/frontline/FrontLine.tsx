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
          makes the front line easy to right-click for fragging. The front-lines layer
          renders above supply routes (MapLayersControl order), so it already wins
          clicks at the FLOT -- no bringToFront needed. A pointer cursor + hover hint
          make the otherwise-hidden right-click discoverable. */}
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
