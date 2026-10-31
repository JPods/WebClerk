/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/store/slices/toastSlice.ts
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type ToastType = "success" | "error" | "info" | "warning";

interface ToastState {
  message: string;
  type: ToastType | null;
  open: boolean;
  /** How long it stays, in ms. */
  duration: number;
}

const initialState: ToastState = {
  message: "",
  type: null,
  open: false,
  duration: 3000,
};

const toastSlice = createSlice({
  name: "toast",
  initialState,
  reducers: {
    showToast(state, action: PayloadAction<{ message: string; type: ToastType; duration?: number }>) {
      state.message = action.payload.message;
      state.type = action.payload.type;
      state.duration = action.payload.duration ?? 3000;
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
