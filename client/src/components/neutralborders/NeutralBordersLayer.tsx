import { selectNeutralBorders } from "../../api/neutralBorderSlice";
import { useAppSelector } from "../../app/hooks";
import {
  AIRSPACE_FILL_ENFORCED,
  AIRSPACE_FILL_OPEN,
  mapColors,
  mapStrokes,
} from "../../theme/mapColors";
import { LayerGroup, Polygon, Tooltip } from "react-leaflet";

// §96: the countries bordering the war, and what happens if you enter them.
//
// Colour says WHO owns the airspace; shading says whether it bites:
//   red   + shade  - hosts the enemy's fields; its own QRA defends it
//   green + shade  - neutral, refuses transit, WILL intercept you
//   green, no shade- neutral, overflight permitted
//   blue,  no shade- hosts your fields; fly through
//
// The DCS F10 map draws the same four, but by then the route is flown. The
// decision the feature asks for -- go around, or go through -- is made in the
// planner, so the lines have to be visible here too.
//
// Renders nothing unless neutral_border_defense is on (the list is empty),
// matching the minefields / culling-zone layers.
export default function NeutralBordersLayer() {
  const borders = useAppSelector(selectNeutralBorders);
  return (
    <LayerGroup>
      {borders.map((border, idx) => {
        const enforced = border.posture === "neutral" && !border.overflight;
        // Red = it will engage you. That covers the enemy's hosts AND a third
        // party that refuses you transit; the two differ by hue, not by family.
        const color =
          border.posture === "red"
            ? mapColors.airspaceRed
            : border.posture === "blue"
            ? mapColors.airspaceBlue
            : enforced
            ? mapColors.airspaceHostileNeutral
            : mapColors.airspaceOpenNeutral;
        // Shaded means dangerous. The enemy's airspace qualifies even though
        // this layer is not what sends the fighters -- its QRA covers it.
        const shaded = enforced || border.posture === "red";
        const stroke = shaded
          ? mapStrokes.airspaceEnforced
          : mapStrokes.airspaceOpen;
        return (
          <Polygon
            key={`neutral-border-${idx}`}
            positions={border.border}
            color={color}
            weight={stroke.weight}
            dashArray={stroke.dashArray}
            fillColor={color}
            // The shade is what makes a country-sized ring read as a region
            // rather than a stray dashed edge. Open airspace gets a faint one
            // rather than none: an unshaded outline was invisible over
            // satellite imagery. It stays well below the enforced shade, so
            // "you may fly here" still never looks like a keep-out block.
            fillOpacity={shaded ? AIRSPACE_FILL_ENFORCED : AIRSPACE_FILL_OPEN}
          >
            <Tooltip sticky>
              <b>{border.country} airspace</b>
              <br />
              {enforced
                ? `Defended below ${border.floor_ft.toLocaleString()} ft · alert from ${
                    border.airfield
                  }`
                : border.airfield}
            </Tooltip>
          </Polygon>
        );
      })}
    </LayerGroup>
  );
}
