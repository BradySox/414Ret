import { useOpenPlaceUnitGroupDialogMutation } from "../../api/liberationApi";
import { selectEnableUnitPlacement } from "../../api/mapSlice";
import { useAppSelector } from "../../app/hooks";
import { useMapEvents } from "react-leaflet";

/**
 * Invisible component that listens for right-clicks on blank map space and
 * opens the Qt drop-spawn dialog (Place Unit Group).
 *
 * Drop-spawn is a cheat (§20): the right-click only opens the dialog when
 * `enable_unit_placement` is on. With it off (default), the contextmenu is left
 * alone so a plain right-click stays free for normal map use — e.g. planning a
 * package against a target. (The server enforces the same gate; skipping the
 * POST here just avoids a pointless round-trip.)
 *
 * Right-clicks on TGO/CP/front-line markers are handled by those components
 * directly (they call openNewPackageDialog) and don't reach this handler.
 */
export default function MapContextMenu() {
  const [openPlaceUnitGroupDialog] = useOpenPlaceUnitGroupDialogMutation();
  const enableUnitPlacement = useAppSelector(selectEnableUnitPlacement);

  useMapEvents({
    contextmenu: (e) => {
      if (!enableUnitPlacement) {
        return;
      }
      openPlaceUnitGroupDialog({ body: { lat: e.latlng.lat, lng: e.latlng.lng } });
    },
  });

  return null;
}
