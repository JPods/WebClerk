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
  /** One button, e.g. Undo: the function is registered in utils/toastActions under `id`. */
  action: { id: string; label: string } | null;
}

const initialState: ToastState = {
  message: "",
  type: null,
  open: false,
  duration: 3000,
  action: null,
};

const toastSlice = createSlice({
  name: "toast",
  initialState,
  reducers: {
    showToast(state, action: PayloadAction<{ message: string; type: ToastType; duration?: number;
                                             action?: { id: string; label: string } | null }>) {
      state.message = action.payload.message;
      state.type = action.payload.type;
      state.duration = action.payload.duration ?? 3000;
      state.action = action.payload.action ?? null;
      state.open = true;
    },
    hideToast(state) {
      state.open = false;
      state.message = "";
      state.type = null;
      state.action = null;
    },
  },
});

export const { showToast, hideToast } = toastSlice.actions;
export default toastSlice.reducer;
