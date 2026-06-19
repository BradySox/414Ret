import { renderWithProviders } from "../../testutils";
import FlightPlansLayer from "./FlightPlansLayer";
import { PropsWithChildren } from "react";

const mockPolyline = jest.fn();
const mockLayerGroup = jest.fn();
jest.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => {
    mockLayerGroup(props);
    return <>{props.children}</>;
  },
  Polyline: require("react").forwardRef((props: any, _ref: any) => {
    mockPolyline(props);
    return null;
  }),
}));

// The waypoints in test data below should all use `should_make: false`. Markers
// need useMap() to check the zoom level to decide if they should be drawn or
// not, and we don't have good options here for mocking that behavior.
describe("FlightPlansLayer", () => {
  describe("unselected flights", () => {
    it("are drawn", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });

      // Each drawn blue flight renders two polylines now: the visible route and
      // a wide invisible hover overlay. Passing a ref to the visible one also
      // Each flight path includes multiple polyline segments.
      expect(mockPolyline).toHaveBeenCalledTimes(4);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn if wrong coalition", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: false,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(2);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn when only selected flights are to be drawn", () => {
      renderWithProviders(<FlightPlansLayer selectedOnly />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: null,
          },
        },
      });
      expect(mockPolyline).not.toHaveBeenCalled();
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
  });
  describe("selected flights", () => {
    it("are drawn", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
              bar: {
                id: "bar",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(4);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn twice", () => {
      renderWithProviders(<FlightPlansLayer blue={true} />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: true,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalledTimes(2);
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
    it("are not drawn if red", () => {
      renderWithProviders(<FlightPlansLayer selectedOnly />, {
        preloadedState: {
          flights: {
            flights: {
              foo: {
                id: "foo",
                blue: false,
                sidc: "",
                waypoints: [
                  {
                    name: "",
                    position: {
                      lat: 0,
                      lng: 0,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                  {
                    name: "",
                    position: {
                      lat: 1,
                      lng: 1,
                    },
                    altitude_ft: 0,
                    altitude_reference: "MSL",
                    is_movable: true,
                    should_mark: false,
                    include_in_path: true,
                    timing: "",
                  },
                ],
              },
            },
            selected: "foo",
          },
        },
      });
      expect(mockPolyline).toHaveBeenCalled();
      expect(mockLayerGroup).toBeCalledTimes(1);
    });
  });
  it("are not drawn if there are no flights", () => {
    renderWithProviders(<FlightPlansLayer blue={true} />);
    expect(mockPolyline).not.toHaveBeenCalled();
    expect(mockLayerGroup).toBeCalledTimes(1);
  });
});
