/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type LoadingState = {
  isApiLoading: boolean;
};

const initialState: LoadingState = {
  isApiLoading: false,
};

const loadingSlice = createSlice({
  name: "loading",
  initialState,
  reducers: {
    setApiLoading: (state, action: PayloadAction<boolean>) => {
      state.isApiLoading = action.payload;
    },
  },
});

export const { setApiLoading } = loadingSlice.actions;
export default loadingSlice.reducer;