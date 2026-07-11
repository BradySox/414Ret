import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { Minefield } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// §57 air-dropped minefields overlay: live BLUE fields (dashed markers). Fed by the
// /game payload; empty unless air_droppable_minefields is on, which hides the layer.
interface MinefieldState {
  fields: Minefield[];
}

const initialState: MinefieldState = {
  fields: [],
};

const minefieldSlice = createSlice({
  name: "minefields",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.fields = action.payload.minefields ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.fields = [];
    });
  },
});

export const selectMinefields = (state: RootState) => state.minefields.fields;

export default minefieldSlice.reducer;
