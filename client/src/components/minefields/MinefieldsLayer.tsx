import { selectMinefields } from "../../api/minefieldSlice";
import { useAppSelector } from "../../app/hooks";
import { mapColors } from "../../theme/mapColors";
import { CircleMarker, LayerGroup, Tooltip } from "react-leaflet";

// §57 air-dropped minefields overlay: a gold dashed marker at each live BLUE field, with
// its remaining mine count. Renders nothing unless air_droppable_minefields is on (the
// field list is empty), matching the supply / restricted-zones layers. BLUE-only: the
// enemy never sees where you mined.
export default function MinefieldsLayer() {
  const fields = useAppSelector(selectMinefields);
  return (
    <LayerGroup>
      {fields.map((field, idx) => (
        <CircleMarker
          key={`minefield-${idx}`}
          center={field.position}
          radius={8}
          color={mapColors.mine}
          weight={2}
          dashArray="4 4"
          fill={true}
          fillColor={mapColors.mine}
          fillOpacity={0.25}
        >
          <Tooltip sticky>
            <b>Minefield</b>
            <br />
            {`${field.charges} mine${field.charges === 1 ? "" : "s"} · ${Math.round(
              field.radius_m
            )} m radius`}
          </Tooltip>
        </CircleMarker>
      ))}
    </LayerGroup>
  );
}
