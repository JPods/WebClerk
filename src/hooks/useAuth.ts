import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { setUser, clearUser, setLoading, setAuthError } from "../store/slices/authSlice";
import { userDetails } from "../api/auth";

export const useAuth = () => {
  const dispatch = useAppDispatch();
  const { user, isAuthenticated, isLoading, error } = useAppSelector((state) => state.auth);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        dispatch(setLoading(true));
        const res = await userDetails();

        if (res.status === 200) {
          const {
            id,
            uuid,
            email,
            role,
            name_first,
            name_middle,
            name_last,
            rank,
            company,
            date_joined,
            salutation,
            attention,
          } = res.data;
          const user = {
            id,
            uuid,
            email,
            role,
            name_first,
            name_middle: name_middle ?? "",
            name_last,
            rank: rank ?? null,
            company: company ?? null,
            date_joined: date_joined ?? null,
            salutation: salutation ?? null,
            attention: attention ?? null,
          };
          dispatch(setUser(user));
        }
      } catch (err: any) {
        dispatch(clearUser());
        dispatch(setAuthError(err?.response?.data?.message || "Failed to fetch user"));
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

