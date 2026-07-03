import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { RestrictedZone } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// ROE restricted zones (campaign phases W4): the active authored phase's
// no-offensive-tasking circles (Route-Package sanctuaries). Fed by the /game
// payload; empty outside authored ROE campaigns, which hides the layer.
interface RestrictedZonesState {
  zones: RestrictedZone[];
  // Free-fire (weapons-free) pockets -- inverted ROE (COIN); drawn green.
  freeFire: RestrictedZone[];
}

const initialState: RestrictedZonesState = {
  zones: [],
  freeFire: [],
};

const restrictedZonesSlice = createSlice({
  name: "restrictedZones",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.zones = action.payload.restricted_zones ?? [];
      state.freeFire = action.payload.free_fire_zones ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.zones = [];
      state.freeFire = [];
    });
  },
});

export const selectRestrictedZones = (state: RootState) =>
  state.restrictedZones.zones;

export const selectFreeFireZones = (state: RootState) =>
  state.restrictedZones.freeFire;

export default restrictedZonesSlice.reducer;
