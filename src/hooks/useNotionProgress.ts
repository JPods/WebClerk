import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchNotionAuthStatus,
  fetchNotionProgress,
  startNotionLogin,
  triggerNotionSync,
  updateNotionModule,
} from "../api/userProfile";
import { NotionModule, NotionProgressResponse } from "../type/notion";

export interface UseNotionProgressState {
  loading: boolean;
  syncing: boolean;
  connecting: boolean;
  error: string | null;
  data: NotionProgressResponse | null;
  refresh: () => Promise<void>;
  syncNow: () => Promise<void>;
  updateModule: (moduleId: string, payload: Partial<NotionModule>) => Promise<void>;
  needsAuth: boolean;
  statusMessage: string | null;
  authUrl: string | null;
  initiateLogin: () => Promise<void>;
}

const NOTION_AUTHORIZE_ENDPOINT = "https://api.notion.com/v1/oauth/authorize";
const NOTION_OAUTH_STATE_KEY = "notion_oauth_state";

const readEnv = (value: unknown): string | null => {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
};

const createState = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
};

const buildNotionAuthorizeUrl = (): string | null => {
  const clientId = readEnv(import.meta.env.VITE_NOTION_CLIENT_ID);
  const redirectUri = readEnv(import.meta.env.VITE_NOTION_REDIRECT_URI);
  const scope = readEnv(import.meta.env.VITE_NOTION_SCOPE);
  const owner = (readEnv(import.meta.env.VITE_NOTION_OAUTH_OWNER) || "user").toLowerCase() === "workspace" ? "workspace" : "user";

  if (!clientId || !redirectUri) {
    return null;
  }

  const state = createState();
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.setItem(NOTION_OAUTH_STATE_KEY, state);
    } catch {
      // ignore storage failures
    }
  }

  const params = new URLSearchParams({
    client_id: clientId,
    response_type: "code",
    owner,
    redirect_uri: redirectUri,
    state,
  });

  if (scope) {
    params.set("scope", scope);
  }

  return `${NOTION_AUTHORIZE_ENDPOINT}?${params.toString()}`;
};

export const useNotionProgress = (): UseNotionProgressState => {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<NotionProgressResponse | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    const status = await fetchNotionAuthStatus();
    const connected = Boolean(status.connected);
    setNeedsAuth(!connected);
    setStatusMessage(status.message ?? null);
    return connected;
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const isConnected = await checkConnection();
      if (!isConnected) {
        setData(null);
        return;
      }

      const response = await fetchNotionProgress();
      setData(response);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        setNeedsAuth(true);
        setError("Connect your Notion account to view progress.");
      } else {
        setError(err?.message || "Failed to load Notion progress");
      }
    } finally {
      setLoading(false);
    }
  }, [checkConnection]);

  const refresh = useMemo(() => load, [load]);

  useEffect(() => {
    load();
  }, [load]);

  const syncNow = useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      if (needsAuth) {
        setError("Connect your Notion account before syncing.");
        return;
      }
      await triggerNotionSync();
      await load();
    } catch (err: any) {
      setError(err?.message || "Failed to sync with Notion");
    } finally {
      setSyncing(false);
    }
  }, [load, needsAuth]);

  const updateModule = useCallback(
    async (moduleId: string, payload: Partial<NotionModule>) => {
      setError(null);
      try {
        if (needsAuth) {
          setError("Connect your Notion account before updating modules.");
          return;
        }
        await updateNotionModule(moduleId, {
          status: payload.status,
          percentComplete: payload.percentComplete,
          notes: payload.description,
        });
        await load();
      } catch (err: any) {
        setError(err?.message || "Failed to update module");
      }
    },
    [load, needsAuth]
  );

  const initiateLogin = useCallback(async () => {
    setConnecting(true);
    setError(null);
    const popup = typeof window !== "undefined" ? window.open("", "_blank", "noopener,noreferrer") : null;
    try {
      let authorizeUrl: string | null | undefined;

      try {
        const { url } = await startNotionLogin();
        authorizeUrl = url;
      } catch (serverErr) {
        console.warn("Falling back to direct Notion authorize URL", serverErr);
      }

      if (!authorizeUrl) {
        authorizeUrl = buildNotionAuthorizeUrl();
      }

      if (!authorizeUrl) {
        throw new Error("Unable to determine Notion authorization URL. Check backend integration or Notion env variables.");
      }

      setAuthUrl(authorizeUrl);

      if (popup && !popup.closed) {
        popup.location.href = authorizeUrl;
        popup.focus();
      } else if (typeof window !== "undefined") {
        window.location.assign(authorizeUrl);
      }
    } catch (err: any) {
      if (popup && !popup.closed) popup.close();
      setError(err?.message || "Failed to initiate Notion login");
    } finally {
      setConnecting(false);
    }
  }, []);

  return {
    loading,
    syncing,
    connecting,
    error,
    data,
    refresh,
    syncNow,
    updateModule,
    needsAuth,
    statusMessage,
    authUrl,
    initiateLogin,
  };
};
