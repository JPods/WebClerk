import { useMemo, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { GridIcon } from "../icons";
import { useWindowManager } from "../context/WindowManagerContext";
import { logout as logoutRequest } from "../api/auth";
import { useAppSelector } from "../store/hooks";
import { clearTokens } from "../api/axios";
import { clearUser } from "../store/slices/authSlice";

type Props = {
  activePath: string;
};

export default function MacTopBar({ activePath }: Props) {
  const { windows, closeWindow, activateWindow } = useWindowManager();
  const { user } = useAppSelector((state) => state.auth);
  const apiBusy = useAppSelector((state) => state.loading.isApiLoading);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const pendingTasks = useMemo(() => windows.filter((w) => w.minimized).length, [windows]);
  const orderedWindows = useMemo(() => [...windows].sort((a, b) => a.openedAt - b.openedAt), [windows]);

  return (
    <div className="sticky top-0 z-[200] flex items-center gap-4 border-b border-slate-200 bg-white/95 px-4 py-2 text-sm text-slate-900 shadow-md backdrop-blur">
      <div className="flex items-center gap-3 text-base font-semibold text-slate-900">
        <GridIcon className="h-5 w-5 text-emerald-500" />
        <span>WebClerk 3.0</span>
        {apiBusy && (
          <div className="flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-800">
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
            Syncing…
          </div>
        )}
      </div>

      <div className="flex flex-1 items-center gap-2 overflow-x-auto">
        {orderedWindows.map((w) => {
          const isActive = w.path === activePath;
          return (
            <div
              key={w.path}
              className={`group flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition ${
                isActive
                  ? "border-emerald-300 bg-white text-slate-900 shadow-sm ring-1 ring-emerald-200"
                  : "border-slate-200 bg-slate-100 text-slate-700 hover:border-slate-300 hover:bg-white"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${isActive ? "bg-emerald-500" : "bg-slate-300"}`} />
              <button
                className="text-left"
                onClick={() => {
                  activateWindow(w.path);
                }}
                title={w.path}
              >
                {w.title}
              </button>
              <div className="flex items-center gap-1">
                {isActive && <span className="text-[10px] font-semibold text-emerald-600">Active</span>}
                {w.minimized && <span className="text-[10px] text-slate-500">min</span>}
                <button
                  className="text-slate-400 hover:text-slate-700"
                  onClick={() => {
                    closeWindow(w.path);
                  }}
                  title="Close"
                >
                    x
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3 text-xs">
        <div className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">Tasks: {pendingTasks}</div>
        <div className="flex items-center gap-2 rounded-full bg-slate-100 px-2 py-1">
          <img
            src="/images/user/owner.jpg"
            alt="avatar"
            className="h-7 w-7 rounded-full border border-white object-cover"
          />
          <div className="leading-tight text-slate-800">
            <p className="text-[11px] text-slate-500">{user?.email || "user"}</p>
            <p className="text-xs font-semibold">{user?.name_first || "Profile"}</p>
          </div>
        </div>
        <button
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          onClick={async () => {
            if (loggingOut) return;
            setLoggingOut(true);
            try {
              await logoutRequest();
            } catch {
              // ignore logout failures
            }
            clearTokens();
            dispatch(clearUser());
            navigate("/");
            setLoggingOut(false);
          }}
        >
          {loggingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>
    </div>
  );
}