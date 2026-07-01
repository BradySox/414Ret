import { RootState } from "../app/store";
import { gameLoaded, gameUnloaded } from "./actions";
import { CampaignStatus } from "./liberationApi";
import { createSlice } from "@reduxjs/toolkit";

// Campaign-status ribbon state (campaign phases W3): turn/date/campaign name +
// the inferred phase (+ political-will meters on Vietnam campaigns). Fed by the
// /game payload's campaign_status; null hides the ribbon entirely (e.g. no game
// loaded, or a pre-feature backend).
interface CampaignStatusState {
  status: CampaignStatus | null;
}

const initialState: CampaignStatusState = {
  status: null,
};

const campaignStatusSlice = createSlice({
  name: "campaignStatus",
  initialState: initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(gameLoaded, (state, action) => {
      state.status = action.payload.campaign_status ?? null;
    });
    builder.addCase(gameUnloaded, (state) => {
      state.status = null;
    });
  },
});

export const selectCampaignStatus = (state: RootState) =>
  state.campaignStatus.status;

export default campaignStatusSlice.reducer;
