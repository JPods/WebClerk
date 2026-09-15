/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/store/slices/toastSlice.ts
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface ToastState {
  message: string;
  type: "success" | "error" | "info" | null;
  open: boolean;
}

const initialState: ToastState = {
  message: "",
  type: null,
  open: false,
};

const toastSlice = createSlice({
  name: "toast",
  initialState,
  reducers: {
    showToast(state, action: PayloadAction<{ message: string; type: "success" | "error" | "info" }>) {
      state.message = action.payload.message;
      state.type = action.payload.type;
      state.open = true;
    },
    hideToast(state) {
      state.open = false;
      state.message = "";
      state.type = null;
    },
  },
});

export const { showToast, hideToast } = toastSlice.actions;
export default toastSlice.reducer;
