import { baseApi as api } from "./baseApi";

const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    listControlPoints: build.query<
      ListControlPointsApiResponse,
      ListControlPointsApiArg
    >({
      query: () => ({ url: `/control-points/` }),
    }),
    getControlPointById: build.query<
      GetControlPointByIdApiResponse,
      GetControlPointByIdApiArg
    >({
      query: (queryArg) => ({ url: `/control-points/${queryArg.cpId}` }),
    }),
    controlPointDestinationInRange: build.query<
      ControlPointDestinationInRangeApiResponse,
      ControlPointDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setControlPointDestination: build.mutation<
      SetControlPointDestinationApiResponse,
      SetControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/destination`,
        method: "PUT",
        body: queryArg.body,
      }),
    }),
    clearControlPointDestination: build.mutation<
      ClearControlPointDestinationApiResponse,
      ClearControlPointDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/control-points/${queryArg.cpId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    getDebugHoldZones: build.query<
      GetDebugHoldZonesApiResponse,
      GetDebugHoldZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/hold/${queryArg.flightId}`,
      }),
    }),
    getDebugJoinZones: build.query<
      GetDebugJoinZonesApiResponse,
      GetDebugJoinZonesApiArg
    >({
      query: (queryArg) => ({
        url: `/debug/waypoint-geometries/join/${queryArg.flightId}`,
      }),
    }),
    listFlights: build.query<ListFlightsApiResponse, ListFlightsApiArg>({
      query: (queryArg) => ({
        url: `/flights/`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getFlightById: build.query<GetFlightByIdApiResponse, GetFlightByIdApiArg>({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}`,
        params: { with_waypoints: queryArg.withWaypoints },
      }),
    }),
    getTacticalOverlayForFlight: build.query<
      GetTacticalOverlayForFlightApiResponse,
      GetTacticalOverlayForFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/flights/${queryArg.flightId}/tactical-overlay`,
      }),
    }),
    listFrontLines: build.query<
      ListFrontLinesApiResponse,
      ListFrontLinesApiArg
    >({
      query: () => ({ url: `/front-lines/` }),
    }),
    getFrontLineById: build.query<
      GetFrontLineByIdApiResponse,
      GetFrontLineByIdApiArg
    >({
      query: (queryArg) => ({ url: `/front-lines/${queryArg.frontLineId}` }),
    }),
    getGameState: build.query<GetGameStateApiResponse, GetGameStateApiArg>({
      query: () => ({ url: `/game/` }),
    }),
    getTerrainZones: build.query<
      GetTerrainZonesApiResponse,
      GetTerrainZonesApiArg
    >({
      query: () => ({ url: `/map-zones/terrain` }),
    }),
    listUnculledZones: build.query<
      ListUnculledZonesApiResponse,
      ListUnculledZonesApiArg
    >({
      query: () => ({ url: `/map-zones/unculled` }),
    }),
    getThreatZones: build.query<
      GetThreatZonesApiResponse,
      GetThreatZonesApiArg
    >({
      query: () => ({ url: `/map-zones/threats` }),
    }),
    getNavmesh: build.query<GetNavmeshApiResponse, GetNavmeshApiArg>({
      query: (queryArg) => ({
        url: `/navmesh/`,
        params: { for_player: queryArg.forPlayer },
      }),
    }),
    openNewFrontLinePackageDialog: build.mutation<
      OpenNewFrontLinePackageDialogApiResponse,
      OpenNewFrontLinePackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/front-line/${queryArg.frontLineId}`,
        method: "POST",
      }),
    }),
    openNewSupplyRoutePackageDialog: build.mutation<
      OpenNewSupplyRoutePackageDialogApiResponse,
      OpenNewSupplyRoutePackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/supply-route/${queryArg.routeId}`,
        method: "POST",
      }),
    }),
    openNewTgoPackageDialog: build.mutation<
      OpenNewTgoPackageDialogApiResponse,
      OpenNewTgoPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openTgoInfoDialog: build.mutation<
      OpenTgoInfoDialogApiResponse,
      OpenTgoInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/tgo/${queryArg.tgoId}`,
        method: "POST",
      }),
    }),
    openNewControlPointPackageDialog: build.mutation<
      OpenNewControlPointPackageDialogApiResponse,
      OpenNewControlPointPackageDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/create-package/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    openControlPointInfoDialog: build.mutation<
      OpenControlPointInfoDialogApiResponse,
      OpenControlPointInfoDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/info/control-point/${queryArg.cpId}`,
        method: "POST",
      }),
    }),
    selectFlight: build.mutation<
      SelectFlightApiResponse,
      SelectFlightApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/select-flight/${queryArg.flightId}`,
        method: "POST",
      }),
    }),
    openPlaceUnitGroupDialog: build.mutation<
      OpenPlaceUnitGroupDialogApiResponse,
      OpenPlaceUnitGroupDialogApiArg
    >({
      query: (queryArg) => ({
        url: `/qt/place-unit-group`,
        method: "POST",
        body: queryArg.body,
      }),
    }),
    deleteUserPlacedTgo: build.mutation<
      DeleteUserPlacedTgoApiResponse,
      DeleteUserPlacedTgoApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}`,
        method: "DELETE",
      }),
    }),
    listSupplyRoutes: build.query<
      ListSupplyRoutesApiResponse,
      ListSupplyRoutesApiArg
    >({
      query: () => ({ url: `/supply-routes/` }),
    }),
    listTgos: build.query<ListTgosApiResponse, ListTgosApiArg>({
      query: () => ({ url: `/tgos/` }),
    }),
    getTgoById: build.query<GetTgoByIdApiResponse, GetTgoByIdApiArg>({
      query: (queryArg) => ({ url: `/tgos/${queryArg.tgoId}` }),
    }),
    tgoDestinationInRange: build.query<
      TgoDestinationInRangeApiResponse,
      TgoDestinationInRangeApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination-in-range`,
        params: { lat: queryArg.lat, lng: queryArg.lng },
      }),
    }),
    setTgoDestination: build.mutation<
      SetTgoDestinationApiResponse,
      SetTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/destination`,
        method: "PUT",
        body: queryArg.body,
      }),
    }),
    clearTgoDestination: build.mutation<
      ClearTgoDestinationApiResponse,
      ClearTgoDestinationApiArg
    >({
      query: (queryArg) => ({
        url: `/tgos/${queryArg.tgoId}/cancel-travel`,
        method: "PUT",
      }),
    }),
    listAllWaypointsForFlight: build.query<
      ListAllWaypointsForFlightApiResponse,
      ListAllWaypointsForFlightApiArg
    >({
      query: (queryArg) => ({ url: `/waypoints/${queryArg.flightId}` }),
    }),
    setWaypointPosition: build.mutation<
      SetWaypointPositionApiResponse,
      SetWaypointPositionApiArg
    >({
      query: (queryArg) => ({
        url: `/waypoints/${queryArg.flightId}/${queryArg.waypointIdx}/position`,
        method: "POST",
        body: queryArg.leafletPoint,
      }),
    }),
    getIadsNetwork: build.query<
      GetIadsNetworkApiResponse,
      GetIadsNetworkApiArg
    >({
      query: () => ({ url: `/iads-network/` }),
    }),
    getIadsConnectionsForTgo: build.query<
      GetIadsConnectionsForTgoApiResponse,
      GetIadsConnectionsForTgoApiArg
    >({
      query: (queryArg) => ({ url: `/iads-network/for-tgo/${queryArg.tgoId}` }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as _liberationApi };
export type ListControlPointsApiResponse =
  /** status 200 Successful Response */ ControlPoint[];
export type ListControlPointsApiArg = void;
export type GetControlPointByIdApiResponse =
  /** status 200 Successful Response */ ControlPoint;
export type GetControlPointByIdApiArg = {
  cpId: string;
};
export type ControlPointDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type ControlPointDestinationInRangeApiArg = {
  cpId: string;
  lat: number;
  lng: number;
};
export type SetControlPointDestinationApiResponse =
  /** status 204 Successful Response */ undefined;
export type SetControlPointDestinationApiArg = {
  cpId: string;
  body: LatLng;
};
export type ClearControlPointDestinationApiResponse =
  /** status 204 Successful Response */ undefined;
export type ClearControlPointDestinationApiArg = {
  cpId: string;
};
export type GetDebugHoldZonesApiResponse =
  /** status 200 Successful Response */ HoldZones;
export type GetDebugHoldZonesApiArg = {
  flightId: string;
};
export type GetDebugJoinZonesApiResponse =
  /** status 200 Successful Response */ JoinZones;
export type GetDebugJoinZonesApiArg = {
  flightId: string;
};
export type ListFlightsApiResponse =
  /** status 200 Successful Response */ Flight[];
export type ListFlightsApiArg = {
  withWaypoints?: boolean;
};
export type GetFlightByIdApiResponse =
  /** status 200 Successful Response */ Flight;
export type GetFlightByIdApiArg = {
  flightId: string;
  withWaypoints?: boolean;
};
export type GetTacticalOverlayForFlightApiResponse =
  /** status 200 Successful Response */ TacticalOverlay;
export type GetTacticalOverlayForFlightApiArg = {
  flightId: string;
};
export type ListFrontLinesApiResponse =
  /** status 200 Successful Response */ FrontLine[];
export type ListFrontLinesApiArg = void;
export type GetFrontLineByIdApiResponse =
  /** status 200 Successful Response */ FrontLine;
export type GetFrontLineByIdApiArg = {
  frontLineId: string;
};
export type GetGameStateApiResponse =
  /** status 200 Successful Response */ Game;
export type GetGameStateApiArg = void;
export type GetTerrainZonesApiResponse =
  /** status 200 Successful Response */ MapZones;
export type GetTerrainZonesApiArg = void;
export type ListUnculledZonesApiResponse =
  /** status 200 Successful Response */ UnculledZone[];
export type ListUnculledZonesApiArg = void;
export type GetThreatZonesApiResponse =
  /** status 200 Successful Response */ ThreatZoneContainer;
export type GetThreatZonesApiArg = void;
export type GetNavmeshApiResponse =
  /** status 200 Successful Response */ NavMesh;
export type GetNavmeshApiArg = {
  forPlayer: boolean;
};
export type OpenNewFrontLinePackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewFrontLinePackageDialogApiArg = {
  frontLineId: string;
};
export type OpenNewSupplyRoutePackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewSupplyRoutePackageDialogApiArg = {
  routeId: string;
};
export type OpenNewTgoPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewTgoPackageDialogApiArg = {
  tgoId: string;
};
export type OpenTgoInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenTgoInfoDialogApiArg = {
  tgoId: string;
};
export type OpenNewControlPointPackageDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenNewControlPointPackageDialogApiArg = {
  cpId: string;
};
export type OpenControlPointInfoDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenControlPointInfoDialogApiArg = {
  cpId: string;
};
export type SelectFlightApiResponse =
  /** status 200 Successful Response */ any;
export type SelectFlightApiArg = {
  flightId: string;
};
export type OpenPlaceUnitGroupDialogApiResponse =
  /** status 200 Successful Response */ any;
export type OpenPlaceUnitGroupDialogApiArg = {
  body: { lat: number; lng: number };
};
export type DeleteUserPlacedTgoApiResponse = undefined;
export type DeleteUserPlacedTgoApiArg = {
  tgoId: string;
};
export type ListSupplyRoutesApiResponse =
  /** status 200 Successful Response */ SupplyRoute[];
export type ListSupplyRoutesApiArg = void;
export type ListTgosApiResponse = /** status 200 Successful Response */ Tgo[];
export type ListTgosApiArg = void;
export type GetTgoByIdApiResponse = /** status 200 Successful Response */ Tgo;
export type GetTgoByIdApiArg = {
  tgoId: string;
};
export type TgoDestinationInRangeApiResponse =
  /** status 200 Successful Response */ boolean;
export type TgoDestinationInRangeApiArg = {
  tgoId: string;
  lat: number;
  lng: number;
};
export type SetTgoDestinationApiResponse =
  /** status 204 Successful Response */ undefined;
export type SetTgoDestinationApiArg = {
  tgoId: string;
  body: LatLng;
};
export type ClearTgoDestinationApiResponse =
  /** status 204 Successful Response */ undefined;
export type ClearTgoDestinationApiArg = {
  tgoId: string;
};
export type ListAllWaypointsForFlightApiResponse =
  /** status 200 Successful Response */ Waypoint[];
export type ListAllWaypointsForFlightApiArg = {
  flightId: string;
};
export type SetWaypointPositionApiResponse =
  /** status 204 Successful Response */ undefined;
export type SetWaypointPositionApiArg = {
  flightId: string;
  waypointIdx: number;
  leafletPoint: LatLng;
};
export type GetIadsNetworkApiResponse =
  /** status 200 Successful Response */ IadsNetwork;
export type GetIadsNetworkApiArg = void;
export type GetIadsConnectionsForTgoApiResponse =
  /** status 200 Successful Response */ IadsConnection[];
export type GetIadsConnectionsForTgoApiArg = {
  tgoId: string;
};
export type LatLng = {
  lat: number;
  lng: number;
};
export type ControlPoint = {
  id: string;
  name: string;
  blue: boolean;
  neutral: boolean;
  position: LatLng;
  mobile: boolean;
  destination?: LatLng;
  sidc: string;
  tacan?: string | null;
  atc_frequency?: string | null;
  units: string[];
  threat_ranges: number[];
  detection_ranges: number[];
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type HoldZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  joinBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type JoinZones = {
  homeBubble: LatLng[][];
  targetBubble: LatLng[][];
  ipBubble: LatLng[][];
  excludedZones: LatLng[][][];
  permissibleZones: LatLng[][][];
  preferredLines: LatLng[][];
};
export type Waypoint = {
  name: string;
  position: LatLng;
  altitude_ft: number;
  altitude_reference: string;
  is_movable: boolean;
  should_mark: boolean;
  include_in_path: boolean;
  timing: string;
};
export type Flight = {
  id: string;
  blue: boolean;
  position?: LatLng;
  sidc: string;
  waypoints?: Waypoint[];
  aircraft?: string;
  num_aircraft?: number;
  flight_type?: string;
  callsign?: string | null;
  package_target?: string;
  package_tot?: string;
};
export type FrontLine = {
  id: string;
  extents: LatLng[];
};
export type TacticalReach = {
  polygon: LatLng[][];
  filled: boolean;
};
export type TacticalTarget = {
  position: LatLng;
};
export type TacticalOverlay = {
  reach: TacticalReach[];
  actual_path?: LatLng[];
  targets: TacticalTarget[];
};
export type Tgo = {
  id: string;
  name: string;
  control_point_name: string;
  category: string;
  blue: boolean;
  position: LatLng;
  units: string[];
  threat_ranges: number[];
  detection_ranges: number[];
  dead: boolean;
  sidc: string;
  task?: string[];
  mobile: boolean;
  destination?: LatLng;
  user_placed: boolean;
  /** COIN concealment: set while this TGO renders as an uncertainty circle;
      `position` is then the jittered circle centre, not the true location. */
  uncertainty_radius_m?: number | null;
  /** Concealed circles sharing this TGO's site (itself included): >= 2 renders
      as the stroke-less density cloud, 1 as the classic dashed ring. */
  concealed_cluster_size?: number | null;
};
export type SupplyRoute = {
  id: string;
  points: LatLng[];
  front_active: boolean;
  is_sea: boolean;
  blue: boolean;
  active_transports: string[];
};
export type IadsConnection = {
  id: string;
  points: LatLng[];
  node: string;
  connected: string;
  active: boolean;
  blue: boolean;
  is_power: boolean;
};
export type IadsNetwork = {
  advanced: boolean;
  connections: IadsConnection[];
};
export type ThreatZones = {
  full: LatLng[][][];
  aircraft: LatLng[][][];
  air_defenses: LatLng[][][];
  radar_sams: LatLng[][][];
};
export type ThreatZoneContainer = {
  blue: ThreatZones;
  red: ThreatZones;
};
export type NavMeshPoly = {
  poly: LatLng[][];
  threatened: boolean;
};
export type NavMesh = {
  polys: NavMeshPoly[];
};
export type NavMeshes = {
  blue: NavMesh;
  red: NavMesh;
};
export type UnculledZone = {
  position: LatLng;
  radius: number;
};
export type CampaignEvent = {
  turn: number;
  title: string;
  text: string;
};
export type VictoryCondition = {
  text: string;
  met: boolean;
  defeat: boolean;
};
export type CampaignStatus = {
  campaign_name?: string | null;
  turn: number;
  date: string;
  blue_supply?: number | null;
  red_supply?: number | null;
  red_c2?: string | null;
  blue_will?: number | null;
  red_will?: number | null;
  blue_will_label?: string | null;
  red_will_label?: string | null;
  blue_will_note?: string | null;
  red_will_note?: string | null;
  victory?: VictoryCondition[];
  victory_description?: string | null;
  will_history?: [number, number, number][];
  events?: CampaignEvent[];
  sitrep_turn?: number | null;
  sitrep_lines?: string[];
  hvt_name?: string | null;
  hvt_turns_left?: number | null;
};
export type SupplyNode = {
  name: string;
  position: LatLng;
  supply: number;
  production: number;
  is_front: boolean;
};
export type Minefield = {
  position: LatLng;
  radius_m: number;
  charges: number;
};
export type DownedPilot = {
  name: string;
  position: LatLng;
  status: string;
  detail: string;
};
export type Game = {
  control_points: ControlPoint[];
  tgos: Tgo[];
  supply_routes: SupplyRoute[];
  front_lines: FrontLine[];
  flights: Flight[];
  iads_network: IadsNetwork;
  threat_zones: ThreatZoneContainer;
  navmeshes: NavMeshes;
  map_center?: LatLng;
  unculled_zones: UnculledZone[];
  map_zones: MapZones;
  blank_canvas_setup: boolean;
  enable_unit_placement: boolean;
  campaign_status?: CampaignStatus | null;
  supply_nodes?: SupplyNode[];
  minefields?: Minefield[];
  downed_pilots?: DownedPilot[];
};
export type MapZones = {
  inclusion: LatLng[][][];
  exclusion: LatLng[][][];
  sea: LatLng[][][];
};
export const {
  useListControlPointsQuery,
  useGetControlPointByIdQuery,
  useControlPointDestinationInRangeQuery,
  useSetControlPointDestinationMutation,
  useClearControlPointDestinationMutation,
  useGetDebugHoldZonesQuery,
  useGetDebugJoinZonesQuery,
  useListFlightsQuery,
  useGetFlightByIdQuery,
  useGetTacticalOverlayForFlightQuery,
  useListFrontLinesQuery,
  useGetFrontLineByIdQuery,
  useGetGameStateQuery,
  useGetTerrainZonesQuery,
  useListUnculledZonesQuery,
  useGetThreatZonesQuery,
  useGetNavmeshQuery,
  useOpenNewFrontLinePackageDialogMutation,
  useOpenNewSupplyRoutePackageDialogMutation,
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
  useOpenNewControlPointPackageDialogMutation,
  useOpenControlPointInfoDialogMutation,
  useSelectFlightMutation,
  useOpenPlaceUnitGroupDialogMutation,
  useDeleteUserPlacedTgoMutation,
  useListSupplyRoutesQuery,
  useListTgosQuery,
  useGetTgoByIdQuery,
  useTgoDestinationInRangeQuery,
  useSetTgoDestinationMutation,
  useClearTgoDestinationMutation,
  useListAllWaypointsForFlightQuery,
  useSetWaypointPositionMutation,
  useGetIadsNetworkQuery,
  useGetIadsConnectionsForTgoQuery,
} = injectedRtkApi;
