import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { DownedPilot } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// §21 downed-aviator overlay: MIA evaders at their last known position + POWs at
// their holding field. Fed by the /game payload; empty when nobody is down, which
// hides the layer.
interface DownedPilotState {
  pilots: DownedPilot[];
}

const initialState: DownedPilotState = {
  pilots: [],
};

const downedPilotSlice = createSlice({
  name: "downedPilots",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.pilots = action.payload.downed_pilots ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.pilots = [];
    });
  },
});

export const selectDownedPilots = (state: RootState) =>
  state.downedPilots.pilots;

export default downedPilotSlice.reducer;
