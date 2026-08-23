/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect } from "react";
import { mapApiProfileToUser, userDetails } from "../../api/auth";
import { bootstrapAuth, clearTokens } from "../../api/axios";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { clearUser, setLoading, setUser } from "../../store/slices/authSlice";

// Syncs Redux auth state with stored tokens/user on initial load and refreshes profile.
// On page load the access token is NOT in localStorage — it lives in memory only.
// bootstrapAuth() sends the httpOnly refresh cookie to /wcapi/token_refresh/ to
// acquire a fresh access token.  If that succeeds we fetch the user profile.
export default function AuthInitializer() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  useEffect(() => {
    let mounted = true;

    // Show cached user immediately while we verify with the server
    if (!user && typeof localStorage !== "undefined") {
      const rawUser = localStorage.getItem("userProfile");
      if (rawUser) {
        try {
          dispatch(setUser(JSON.parse(rawUser)));
        } catch {
          // Ignore malformed cache
        }
      }
    }

    const hydrate = async () => {
      dispatch(setLoading(true));
      try {
        // 1. Try to recover access token from httpOnly refresh cookie
        const token = await bootstrapAuth();
        if (!token) {
          // No valid session — clear everything
          clearTokens();
          if (typeof localStorage !== "undefined") localStorage.removeItem("userProfile");
          dispatch(clearUser());
          return;
        }

        // 2. Token recovered — fetch authoritative profile
        const resp = await userDetails();
        if (resp?.status === 200) {
          const mapped = mapApiProfileToUser(resp.data);
          if (typeof localStorage !== "undefined") {
            localStorage.setItem("userProfile", JSON.stringify(mapped));
          }
          dispatch(setUser(mapped));
        } else {
          clearTokens();
          if (typeof localStorage !== "undefined") localStorage.removeItem("userProfile");
          dispatch(clearUser());
        }
      } catch {
        clearTokens();
        if (typeof localStorage !== "undefined") localStorage.removeItem("userProfile");
        dispatch(clearUser());
      } finally {
        if (mounted) dispatch(setLoading(false));
      }
    };

    hydrate();

    return () => {
      mounted = false;
    };
    // Run once on app load to hydrate auth state
  }, [dispatch]);

  return null;
}