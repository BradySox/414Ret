import backend from "../../api/backend";
import reloadGameState from "../../api/gamestate";
import { useAppDispatch } from "../../app/hooks";
import { LayerGroup } from "react-leaflet";

// Empty layer wrapped in a LayersControl.Overlay (same pattern as the radar
// emitter highlight toggle). Toggling the overlay flips the server-side
// fog-of-war "overview" flag and re-pulls full game state, so the map redraws
// with (or without) the otherwise-fogged enemy composition, threat/detection
// rings, and hidden command posts. View-only: never persisted, defaults off.
export default function FogOfWarToggle() {
  const dispatch = useAppDispatch();
  const setReveal = (revealed: boolean) => {
    backend
      .put("/fog-of-war/reveal", null, { params: { revealed } })
      .then(() => reloadGameState(dispatch, true))
      .catch((error) => console.log(`Error toggling fog of war: ${error}`));
  };
  return (
    <LayerGroup
      eventHandlers={{
        add: () => setReveal(true),
        remove: () => setReveal(false),
      }}
    />
  );
}
