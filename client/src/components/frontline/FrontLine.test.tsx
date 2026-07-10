import { renderWithProviders } from "../../testutils";
import FrontLine from "./FrontLine";
import { PolylineProps } from "react-leaflet";

const mockPolyline = jest.fn();
jest.mock("react-leaflet", () => ({
  Polyline: (props: PolylineProps) => {
    mockPolyline(props);
  },
  // The interactive hit-line renders a <Tooltip> child (right-click hint); stub it so
  // the mocked react-leaflet module still resolves the import.
  Tooltip: () => null,
}));

describe("FrontLine", () => {
  it("is drawn in the correct location", () => {
    const extents = [
      { lat: 0, lng: 0 },
      { lat: 1, lng: 0 },
    ];
    renderWithProviders(
      <FrontLine
        front={{
          id: "",
          extents: extents,
        }}
      />
    );
    expect(mockPolyline).toHaveBeenCalledWith(
      expect.objectContaining({
        positions: extents,
      })
    );
  });
});
