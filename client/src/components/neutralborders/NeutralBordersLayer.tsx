import { selectNeutralBorders } from "../../api/neutralBorderSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors, mapStrokes } from "../../theme/mapColors";
import { LayerGroup, Polygon, Tooltip } from "react-leaflet";

// §96 neutral border defense: the defended airspace of each authored neutral
// country, drawn as an amber dashed ring with a barely-there fill.
//
// The DCS F10 map already draws this, but by then the route is flown. The whole
// decision the feature asks for -- cut the corner or go around -- is made in the
// planner, so the line has to be visible here. The tooltip carries the altitude
// floor, because a border you can legally overfly at height is a different
// obstacle from one you cannot.
//
// Renders nothing unless neutral_border_defense is on (the list is empty),
// matching the minefields / culling-zone layers.
export default function NeutralBordersLayer() {
  const borders = useAppSelector(selectNeutralBorders);
  return (
    <LayerGroup>
      {borders.map((border, idx) => (
        <Polygon
          key={`neutral-border-${idx}`}
          positions={border.border}
          color={mapColors.neutralBorder}
          weight={mapStrokes.neutralBorder.weight}
          dashArray={mapStrokes.neutralBorder.dashArray}
          fillColor={mapColors.neutralBorder}
          fillOpacity={0.04}
        >
          <Tooltip sticky>
            <b>{border.country} airspace</b>
            <br />
            {`Defended below ${border.floor_ft.toLocaleString()} ft · alert from ${
              border.airfield
            }`}
          </Tooltip>
        </Polygon>
      ))}
    </LayerGroup>
  );
}
