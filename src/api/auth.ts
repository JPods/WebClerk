import apiClient, { authClient } from "./axios"; // separated clients
import { EmailVerifyFormData, RegisterFormData } from "../validations/auth"; // Adjust the import path as necessary
import { AuthURL, PostLoginURL } from "../routes/network"; // Adjust the import path as necessary
import { User } from "../store/slices/authSlice";

// Keys that identify a payload containing user profile attributes
const USER_SHAPE_KEYS = new Set([
  "id",
  "uuid",
  "email",
  "role",
  "name_first",
  "name_last",
]);

// Drill into axios/envelope wrappers until we reach an object with user fields
const unwrapUserPayload = (value: any): any => {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return value;
  }

  const visited = new Set<any>();
  let current: any = value;

  while (current && typeof current === "object" && !Array.isArray(current)) {
    if (visited.has(current)) {
      break;
    }
    visited.add(current);

    const keys = Object.keys(current);
    const hasUserKeys = keys.some((key) => USER_SHAPE_KEYS.has(key));
    if (hasUserKeys) {
      return current;
    }

    if (
      Object.prototype.hasOwnProperty.call(current, "user") &&
      current.user &&
      typeof current.user === "object" &&
      !Array.isArray(current.user)
    ) {
      current = current.user;
      continue;
    }

    if (
      Object.prototype.hasOwnProperty.call(current, "data") &&
      current.data &&
      typeof current.data === "object" &&
      !Array.isArray(current.data)
    ) {
      current = current.data;
      continue;
    }

    break;
  }

  return current;
};

// Preserve role data as string or array while stripping obvious noise
const normalizeRole = (rawRole: unknown): string | string[] => {
  if (Array.isArray(rawRole)) {
    return rawRole
      .map((value) => (typeof value === "string" ? value : String(value)))
      .filter((value) => value.trim() !== "");
  }

  if (typeof rawRole === "string") {
    return rawRole;
  }

  if (rawRole == null) {
    return "";
  }

  return String(rawRole);
};

export const mapApiProfileToUser = (input: any): User => {
  const raw = unwrapUserPayload(input) ?? {};

  return {
    id: raw.id ?? raw.pk ?? "",
    uuid: raw.uuid ?? "",
    email: raw.email ?? "",
    role: normalizeRole(raw.role ?? raw.roles),
    name_first: raw.name_first ?? raw.first_name ?? "",
    name_middle: raw.name_middle ?? raw.middle_name ?? null,
    name_last: raw.name_last ?? raw.last_name ?? "",
    rank: raw.rank ?? null,
    company: raw.company ?? null,
    date_joined: raw.date_joined ?? raw.joined_at ?? null,
    salutation: raw.salutation ?? null,
    attention: raw.attention ?? null,
  };
};

export const login = async (credentials:any) => {
  try {
  const res = await authClient.post(AuthURL.LOGIN, credentials);
    return res.data.data;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};

export const signup = async (userData: RegisterFormData) => {
  const res = await authClient.post(AuthURL.SIGNUP, userData);
  return res;
};

export const logout = async () => {
  try {
        const refreshToken = localStorage.getItem("refreshToken");
  const res = await authClient.post(AuthURL.LOGOUT,{
            refresh:refreshToken,
        });
        localStorage.clear();
        return res.data;
  } catch (error:any) {
        return error.response?.status || error.message
  }
};

export const userDetails = async () => {
  try {
  const res = await apiClient.get(PostLoginURL.getUser);
    return res;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};

export const verifyEmail = async (userData:EmailVerifyFormData) => {
  try {
  const res = await authClient.post(AuthURL.verifyEmail, userData);
    return res;
  }
  catch (error: any) {
    return error.response?.data || error.message
  }
};