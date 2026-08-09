import { renderWithProviders } from "../../testutils";
import FrontLinesLayer from "./FrontLinesLayer";
import { PropsWithChildren } from "react";

const mockPolyline = jest.fn();
const mockLayerGroup = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => {
    mockLayerGroup(props);
    return <>{props.children}</>;
  },
  Polyline: (props: any) => {
    mockPolyline(props);
  },
  // FrontLine's interactive hit-line renders a <Tooltip> child (right-click hint);
  // stub it so the mocked react-leaflet module still resolves the import.
  Tooltip: () => null,
  // The fronts render inside a dedicated z-450 <Pane> so their contextmenu stays
  // reachable under the flight-plan hit overlay (upstream #921). A mocked module
  // replaces the WHOLE module, so anything the component imports must be stubbed
  // here or it arrives undefined and React throws "Element type is invalid".
  Pane: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));

// The waypoints in test data below should all use `should_make: false`. Markers
// need useMap() to check the zoom level to decide if they should be drawn or
// not, and we don't have good options here for mocking that behavior.
describe("FrontLinesLayer", () => {
  it("draws nothing when there are no front lines", () => {
    renderWithProviders(<FrontLinesLayer />);
    expect(mockPolyline).not.toHaveBeenCalled();
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
  });

  it("draws front lines", () => {
    const extents = [
      { lat: 0, lng: 0 },
      { lat: 1, lng: 1 },
    ];
    renderWithProviders(<FrontLinesLayer />, {
      preloadedState: {
        frontLines: {
          fronts: {
            foo: {
              id: "foo",
              extents: extents,
            },
            bar: {
              id: "bar",
              extents: extents,
            },
          },
        },
      },
    });
    // Each front line draws two polylines: the visible weight-16 line and a wide,
    // invisible hit line for right-clicking (2 fronts x 2 = 4).
    expect(mockPolyline).toHaveBeenCalledTimes(4);
    expect(mockPolyline).toHaveBeenCalledWith(
      expect.objectContaining({
        positions: extents,
      })
    );
    expect(mockLayerGroup).toHaveBeenCalledTimes(1);
  });
});
