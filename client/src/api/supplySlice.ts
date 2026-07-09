import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { SupplyNode } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// War-economy supply-flow overlay (§53 P4b): BLUE fronts + producers with their
// materiel readiness. Fed by the /game payload; empty unless war_economy is on,
// which hides the layer.
interface SupplyState {
  nodes: SupplyNode[];
}

const initialState: SupplyState = {
  nodes: [],
};

const supplySlice = createSlice({
  name: "supply",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.nodes = action.payload.supply_nodes ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.nodes = [];
    });
  },
});

export const selectSupplyNodes = (state: RootState) => state.supply.nodes;

export default supplySlice.reducer;
