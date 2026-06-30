import {
  FrontLine as FrontLineModel,
  useOpenNewFrontLinePackageDialogMutation,
} from "../../api/liberationApi";
import { Polyline as LPolyline } from "leaflet";
import { useEffect, useRef } from "react";
import { Polyline } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const [openNewPackageDialog] = useOpenNewFrontLinePackageDialogMutation();
  const hit = useRef<LPolyline | null>();

  useEffect(() => {
    // Keep the front-line hit target on top so it wins right-clicks at the FLOT,
    // where the supply-route hit line and threat zones overlap it.
    hit.current?.bringToFront();
  });

  return (
    <>
      <Polyline positions={props.front.extents} weight={16} color={"#fe7d0a"} />
      {/* The visible line spans only the conflict zone (~20-30 km on compressed
          campaigns) at weight 16 -- a small target. This wide, invisible hit line
          makes the front line easy to right-click for fragging; bringToFront keeps it
          above the supply-route hit line. */}
      <Polyline
        positions={props.front.extents}
        pathOptions={{ opacity: 0, weight: 28 }}
        ref={(ref) => (hit.current = ref)}
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
