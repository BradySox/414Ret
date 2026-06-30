import {
  FrontLine as FrontLineModel,
  useOpenNewFrontLinePackageDialogMutation,
} from "../../api/liberationApi";
import { Polyline } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const [openNewPackageDialog] = useOpenNewFrontLinePackageDialogMutation();
  return (
    <>
      <Polyline positions={props.front.extents} weight={16} color={"#fe7d0a"} />
      {/* The visible line spans only the conflict zone (~20-30 km on compressed
          campaigns) at weight 16 -- a small target. This wide, invisible hit line
          makes the front line easy to right-click for fragging. The front-lines layer
          renders above supply routes (MapLayersControl order), so it already wins
          clicks at the FLOT -- no bringToFront needed. */}
      <Polyline
        positions={props.front.extents}
        pathOptions={{ opacity: 0, weight: 28 }}
        eventHandlers={{
          contextmenu: () => {
            openNewPackageDialog({ frontLineId: props.front.id });
          },
        }}
      />
    </>
  );
}

export default FrontLine;
