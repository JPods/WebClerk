import { useEffect } from "react";
import { mapApiProfileToUser, userDetails } from "../../api/auth";
import { clearTokens } from "../../api/axios";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { clearUser, setLoading, setUser } from "../../store/slices/authSlice";

// Syncs Redux auth state with stored tokens/user on initial load and refreshes profile
export default function AuthInitializer() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  useEffect(() => {
    let mounted = true;

    const storedToken =
      typeof localStorage !== "undefined" ? localStorage.getItem("accessToken") : null;

    if (!storedToken) {
      clearTokens();
      if (typeof localStorage !== "undefined") localStorage.removeItem("userProfile");
      dispatch(clearUser());
      return;
    }

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

    const fetchProfile = async () => {
      dispatch(setLoading(true));
      try {
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

    fetchProfile();

    return () => {
      mounted = false;
    };
  // Run once on app load to hydrate auth state
  }, [dispatch]);

  return null;
}