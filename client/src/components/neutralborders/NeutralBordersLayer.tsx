import { selectNeutralBorders } from "../../api/neutralBorderSlice";
import { useAppSelector } from "../../app/hooks";
import {
  AIRSPACE_FILL_BELLIGERENT,
  AIRSPACE_FILL_ENFORCED,
  AIRSPACE_FILL_OPEN,
  mapColors,
  mapStrokes,
} from "../../theme/mapColors";
import { CasedPolygon } from "../map/CasedShapes";
import { LayerGroup, Tooltip } from "react-leaflet";

// §96: every country on the map, and what its airspace does to you.
//
// Two channels, and they answer different questions.
//
//   HUE  - whose airspace: red enemy-held, blue friendly, grey fought over by
//          both, mint uninvolved.
//   SHADE- will it intercept you. Only ONE state does: a country not in the
//          war that refuses you transit. That state alone gets a real fill.
//
// A country in the war is drawn as a solid outline over a faint wash. Its sky
// is governed by its own side's QRA, not by this feature, and its allegiance is
// already carried by the unit icons, the threat rings and the front line --
// filling it as heavily as a hostile neutral washed half the Syria map pink.
// Dashes are reserved for a boundary you have to make a decision about.
//
// Every stroke is CASED (the dark halo the rest of the overlay family uses).
// Without it a friendly country's blue line was lost among the blue flight
// paths and read as its enforcing neighbour's crimson -- a faint line is not a
// quiet line, it is an absent one.
//
// The DCS F10 map draws the same states, but by then the route is flown. The
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
        const belligerent = border.posture !== "neutral";
        const enforced = !belligerent && !border.overflight;
        const color =
          border.posture === "red"
            ? mapColors.airspaceRed
            : border.posture === "blue"
            ? mapColors.airspaceBlue
            : border.posture === "contested"
            ? mapColors.airspaceContested
            : enforced
            ? mapColors.airspaceHostileNeutral
            : mapColors.airspaceOpenNeutral;
        const stroke = belligerent
          ? mapStrokes.airspaceBelligerent
          : enforced
          ? mapStrokes.airspaceEnforced
          : mapStrokes.airspaceOpen;
        const fillOpacity = belligerent
          ? AIRSPACE_FILL_BELLIGERENT
          : enforced
          ? AIRSPACE_FILL_ENFORCED
          : AIRSPACE_FILL_OPEN;
        return (
          <CasedPolygon
            key={`neutral-border-${idx}`}
            positions={border.border}
            color={color}
            signature={stroke}
            fillColor={color}
            fillOpacity={fillOpacity}
          >
            <Tooltip sticky>
              <b>{border.country} airspace</b>
              <br />
              {enforced
                ? // No floor means no safe altitude, so the tooltip must not
                  // imply one exists by naming a number.
                  `${
                    border.floor_ft
                      ? `Defended below ${border.floor_ft.toLocaleString()} ft`
                      : "Closed to you at any altitude"
                  } · alert from ${border.airfield}`
                : border.airfield}
            </Tooltip>
          </CasedPolygon>
        );
      })}
    </LayerGroup>
  );
}
