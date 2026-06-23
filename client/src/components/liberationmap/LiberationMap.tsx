import { selectMapCenter } from "../../api/mapSlice";
import { useAppSelector } from "../../app/hooks";
import CullingExclusionZones from "../cullingexclusionzones/CullingExclusionZones";
import MapLayersControl from "../maplayers/MapLayersControl";
import NavMeshLayer from "../navmesh/NavMeshLayer";
import LeafletRuler from "../ruler/Ruler";
import TerrainZonesLayers from "../terrainzones/TerrainZonesLayers";
import { CoalitionThreatZones } from "../threatzones";
import { WaypointDebugZonesControls } from "../waypointdebugzones/WaypointDebugZonesControls";
import "./LiberationMap.css";
import { Map } from "leaflet";
import { useEffect, useRef } from "react";
import { LayersControl, MapContainer, ScaleControl } from "react-leaflet";

export default function LiberationMap() {
  const map = useRef<Map>(null);
  const mapCenter = useAppSelector(selectMapCenter);
  useEffect(() => {
    map.current?.setView(mapCenter, map.current?.getZoom() ?? 8, { animate: true, duration: 1 });
  });
  return (
    <MapContainer zoom={map.current?.getZoom() ?? 8} zoomControl={false} ref={map}>
      <ScaleControl />
      <LeafletRuler />
      <MapLayersControl />
      <LayersControl position="topleft">
        <CoalitionThreatZones blue={true} />
        <CoalitionThreatZones blue={false} />
        <LayersControl.Overlay name="Blue navmesh">
          <NavMeshLayer blue={true} />
        </LayersControl.Overlay>
        <LayersControl.Overlay name="Red navmesh">
          <NavMeshLayer blue={false} />
        </LayersControl.Overlay>
        <TerrainZonesLayers />
        <CullingExclusionZones />
        <WaypointDebugZonesControls />
      </LayersControl>
    </MapContainer>
  );
}
