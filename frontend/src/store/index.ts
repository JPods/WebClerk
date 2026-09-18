/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/store/index.ts
import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./slices/authSlice";
import configReducer from "./slices/configSlice";
import loadingReducer from "./slices/loadingSlice";
import toastReducer from "./slices/toastSlice";
import companyReducer from "./slices/companySlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    config: configReducer,
    loading: loadingReducer,
    toast: toastReducer,
    company: companyReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
