import { ControlPoint } from "../../api/_liberationApi";
import backend from "../../api/backend";

function openInfoDialog(controlPoint: ControlPoint) {
  backend.post(`/qt/info/control-point/${controlPoint.id}`);
}

function openNewPackageDialog(controlPoint: ControlPoint) {
  backend.post(`/qt/create-package/control-point/${controlPoint.id}`);
}

// Campaign-maker blank-canvas paint: cycle a base's ownership. Left-click goes
// forward neutral (gray) -> blue -> red -> neutral; right-click goes backward.
// The server pushes an SSE update so the marker recolors without a refresh.
type Coalition = "blue" | "red" | "neutral";

function currentCoalition(controlPoint: ControlPoint): Coalition {
  if (controlPoint.neutral) {
    return "neutral";
  }
  return controlPoint.blue ? "blue" : "red";
}

function paintControlPoint(controlPoint: ControlPoint, forward: boolean) {
  const order: Coalition[] = ["neutral", "blue", "red"];
  const idx = order.indexOf(currentCoalition(controlPoint));
  const step = forward ? 1 : order.length - 1;
  const next = order[(idx + step) % order.length];
  backend.put(`/control-points/${controlPoint.id}/coalition`, {
    coalition: next,
  });
}

export const makeLocationMarkerEventHandlers = (
  controlPoint: ControlPoint,
  blankCanvasSetup: boolean = false
) => {
  if (blankCanvasSetup) {
    return {
      click: () => {
        paintControlPoint(controlPoint, true);
      },

      contextmenu: () => {
        paintControlPoint(controlPoint, false);
      },
    };
  }

  return {
    click: () => {
      openInfoDialog(controlPoint);
    },

    contextmenu: () => {
      openNewPackageDialog(controlPoint);
    },
  };
};
