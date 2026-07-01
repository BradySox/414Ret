import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { RestrictedZone } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// ROE restricted zones (campaign phases W4): the active authored phase's
// no-offensive-tasking circles (Route-Package sanctuaries). Fed by the /game
// payload; empty outside authored ROE campaigns, which hides the layer.
interface RestrictedZonesState {
  zones: RestrictedZone[];
}

const initialState: RestrictedZonesState = {
  zones: [],
};

const restrictedZonesSlice = createSlice({
  name: "restrictedZones",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.zones = action.payload.restricted_zones ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.zones = [];
    });
  },
});

export const selectRestrictedZones = (state: RootState) =>
  state.restrictedZones.zones;

export default restrictedZonesSlice.reducer;
