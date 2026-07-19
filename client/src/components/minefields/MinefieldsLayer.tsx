import { selectMinefields } from "../../api/minefieldSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors, mapStrokes } from "../../theme/mapColors";
import { CasedCircleMarker } from "../map/CasedShapes";
import { LayerGroup, Tooltip } from "react-leaflet";

// §57 air-dropped minefields overlay: a gold tick-marked (hazard signature) marker at
// each live BLUE field, cased so it reads over any imagery, with its remaining mine
// count. Renders nothing unless air_droppable_minefields is on (the field list is
// empty), matching the supply / restricted-zones layers. BLUE-only: the enemy never
// sees where you mined.
export default function MinefieldsLayer() {
  const fields = useAppSelector(selectMinefields);
  return (
    <LayerGroup>
      {fields.map((field, idx) => (
        <CasedCircleMarker
          key={`minefield-${idx}`}
          center={field.position}
          radius={8}
          color={mapColors.mine}
          signature={mapStrokes.minefield}
          fillOpacity={0.25}
        >
          <Tooltip sticky>
            <b>Minefield</b>
            <br />
            {`${field.charges} mine${field.charges === 1 ? "" : "s"} · ${Math.round(
              field.radius_m
            )} m radius`}
          </Tooltip>
        </CasedCircleMarker>
      ))}
    </LayerGroup>
  );
}
