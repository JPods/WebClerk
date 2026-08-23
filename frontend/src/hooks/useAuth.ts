/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { setUser, clearUser, setLoading, setAuthError } from "../store/slices/authSlice";
import { userDetails, mapApiProfileToUser } from "../api/auth";

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error } = useAppSelector((state) => state.auth);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        dispatch(setLoading(true));
        const res = await userDetails();
        const isAxiosResponse =
          res && typeof res === "object" && "status" in res;

        if (isAxiosResponse && (res as any).status === 200) {
          dispatch(setUser(mapApiProfileToUser((res as any).data)));
          dispatch(setAuthError(null));
          return;
        }

        const message =
          (isAxiosResponse && ((res as any)?.data?.message || (res as any)?.message)) ||
          (typeof res === "string" ? res : "Failed to fetch user");

        throw new Error(message);
      } catch (err: any) {
        dispatch(clearUser());
        const fallbackMessage =
          err?.response?.data?.message || err?.message || "Failed to fetch user";
        dispatch(setAuthError(fallbackMessage));
      } finally {
        dispatch(setLoading(false));
      }
    };

    if (!isAuthenticated) {
      fetchUser();
    }
  }, [dispatch, isAuthenticated]);

  return { user, isAuthenticated, isLoading, error };
};

