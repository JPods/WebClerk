import { useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import axiosInstance from "../api/axios";
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
        //dispatch(setUser(res.data));
         dispatch(setUser({ ...res.return_data.user, isAuthenticated: true }));
      } catch (err: any) {
        dispatch(clearUser());
        dispatch(setAuthError(err?.response?.data?.message || "Failed to fetch user"));
      } finally {
        dispatch(setLoading(false));
      }
    };

    if (!user && !isAuthenticated) {
      fetchUser();
    }
  }, [dispatch, user, isAuthenticated]);

  return { user, isAuthenticated, isLoading, error };
};

