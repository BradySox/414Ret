import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { NeutralBorder } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// §96 neutral border defense: the defended airspace of each authored neutral
// country. Fed by the /game payload; empty unless neutral_border_defense is on,
// which hides the layer. Never fogged -- a national border is public knowledge,
// and seeing the line is the whole point of the layer.
interface NeutralBorderState {
  borders: NeutralBorder[];
}

const initialState: NeutralBorderState = {
  borders: [],
};

const neutralBorderSlice = createSlice({
  name: "neutralBorders",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.borders = action.payload.neutral_borders ?? [];
    });
    builder.addCase(gameUnloaded, (state) => {
      state.borders = [];
    });
  },
});

export const selectNeutralBorders = (state: RootState) =>
  state.neutralBorders.borders;

export default neutralBorderSlice.reducer;
