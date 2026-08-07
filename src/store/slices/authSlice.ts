/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
// src/store/slices/authSlice.ts
import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface User {
  id: string | number;
  uuid?: string;
  email: string;
  role: string | string[];
  name_first: string;
  name_middle?: string | null;
  name_last: string;
  rank?: string | null;
  company?: string | null;
  date_joined?: string | null;
  salutation?: string | null;
  attention?: string | null;
  prefs?: Record<string, any> | null;
  is_staff?: boolean;
  is_superuser?: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

const readStoredUser = (): User | null => {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem("userProfile");
    if (!raw) return null;
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
};

const initialUser = readStoredUser();

const initialState: AuthState = {
  user: initialUser,
  // Access tokens live in memory only — we cannot check on module load.
  // Optimistically treat a cached user profile as "likely authenticated".
  // AuthInitializer will confirm via bootstrapAuth() and update these.
  isAuthenticated: Boolean(initialUser),
  // Always start loading so AuthInitializer has time to call bootstrapAuth.
  isLoading: true,
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setUser(state, action: PayloadAction<User>) {
      state.user = action.payload;
      state.isAuthenticated = true;
    },
    clearUser(state) {
      state.user = null;
      state.isAuthenticated = false;
    },
    setLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    setAuthError: (state, action) => {
      state.error = action.payload;
    },
  },
});

export const { setUser, clearUser, setLoading, setAuthError } = authSlice.actions;
export default authSlice.reducer;
