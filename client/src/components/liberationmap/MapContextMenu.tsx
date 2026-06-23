import { useOpenPlaceUnitGroupDialogMutation } from "../../api/liberationApi";
import { useMapEvents } from "react-leaflet";

/**
 * Invisible component that listens for right-clicks on blank map space and
 * opens the Qt drop-spawn dialog (Place Unit Group).
 *
 * Right-clicks on TGO/CP/front-line markers are handled by those components
 * directly (they call openNewPackageDialog). This component only fires when
 * the event reaches the map canvas without being consumed first.
 */
export default function MapContextMenu() {
  const [openPlaceUnitGroupDialog] = useOpenPlaceUnitGroupDialogMutation();

  useMapEvents({
    contextmenu: (e) => {
      openPlaceUnitGroupDialog({ body: { lat: e.latlng.lat, lng: e.latlng.lng } });
    },
  });

  return null;
}
