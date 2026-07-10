import {
  SupplyRoute as SupplyRouteModel,
  useOpenNewSupplyRoutePackageDialogMutation,
} from "../../api/liberationApi";
import { mapColors } from "../../theme/mapColors";
import SplitLines from "../splitlines/SplitLines";
import { Polyline as LPolyline } from "leaflet";
import { useEffect, useRef } from "react";
import { Polyline, Tooltip } from "react-leaflet";

interface SupplyRouteProps {
  route: SupplyRouteModel;
}

// The right-click frag only lands on an ENEMY route (a friendly route 404s server-side),
// so the interdiction hint shows only there.
function InterdictionHint(props: SupplyRouteProps) {
  if (props.route.blue) {
    return null;
  }
  return (
    <>
      <br />
      <i>Right-click: frag interdiction</i>
    </>
  );
}

function SupplyRouteTooltip(props: SupplyRouteProps) {
  if (!props.route.active_transports.length) {
    return (
      <Tooltip>
        This supply route is inactive.
        <InterdictionHint {...props} />
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <SplitLines items={props.route.active_transports} />
      <InterdictionHint {...props} />
    </Tooltip>
  );
}

function ActiveSupplyRouteHighlight(props: SupplyRouteProps) {
  if (!props.route.active_transports.length) {
    return <></>;
  }

  return (
    <Polyline
      positions={props.route.points}
      color={mapColors.routeActive}
      weight={2}
    />
  );
}

function colorFor(route: SupplyRouteModel) {
  if (route.front_active) {
    return mapColors.routeContested;
  }
  if (route.blue) {
    return mapColors.routeFriendly;
  }
  return mapColors.routeEnemy;
}

export default function SupplyRoute(props: SupplyRouteProps) {
  const color = colorFor(props.route);
  const weight = props.route.is_sea ? 4 : 6;
  const [openInterdictionPackage] = useOpenNewSupplyRoutePackageDialogMutation();

  const path = useRef<LPolyline | null>();

  useEffect(() => {
    // Ensure that the highlight line draws on top of this. We have to bring
    // this to the back rather than bringing the highlight to the front because
    // the highlight won't necessarily be drawn yet.
    path.current?.bringToBack();
  });

  return (
    <>
      <Polyline
        positions={props.route.points}
        pathOptions={{ color: color, weight: weight }}
        ref={(ref) => (path.current = ref)}
      >
        <ActiveSupplyRouteHighlight {...props} />
      </Polyline>
      {/* A fat, invisible hit line. The visible route above is only weight 6 and is
          sent to the back (so the active-transport highlight draws on top), which makes
          it nearly impossible to right-click directly. This wide overlay is the actual
          target for the hover tooltip and the right-click interdiction frag. Threat
          zones are non-interactive and this layer renders below the front lines, so the
          wide hit line does not swallow their clicks. */}
      <Polyline
        positions={props.route.points}
        pathOptions={{ opacity: 0, weight: 16, className: "map-interactive" }}
        eventHandlers={{
          // Right-click an enemy supply route to frag an Armed Recon interdiction
          // package against its enemy end. The server no-ops (404) for a friendly route.
          contextmenu: () => {
            openInterdictionPackage({ routeId: props.route.id });
          },
        }}
      >
        <SupplyRouteTooltip {...props} />
      </Polyline>
    </>
  );
}
