/* LastChecked: 2026-07-19 | WhereUsed: Main layout top bar | WhoCreated: Unknown */
import { useMemo, useState } from "react";

/** Detail view preference — "app" = .tsx pages, "admin" = DataBrowser detail */
export function getDetailViewPref(): 'app' | 'admin' {
  return (localStorage.getItem('wc3_detail_view_pref') as 'app' | 'admin') || 'app';
}
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { FiLogOut } from "react-icons/fi";
import { FaBoxes } from "react-icons/fa";
import { GridIcon } from "../icons";
import { useWindowManager } from "../context/WindowManagerContext";
import { logout as logoutRequest } from "../api/auth";
import { useAppSelector } from "../store/hooks";
import { clearTokens } from "../api/axios";
import { clearUser } from "../store/slices/authSlice";
import TaskManagerIndicator from "../components/header/TaskManagerIndicator";
import InventoryMonitor from "../components/header/InventoryMonitor";
import HelpMenu from "../components/common/HelpMenu";

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
  const [showInventoryMonitor, setShowInventoryMonitor] = useState(false);
  const [detailView, setDetailView] = useState<'app' | 'admin'>(() => getDetailViewPref());
  const [btnStyle, setBtnStyle] = useState(() => localStorage.getItem('wc3_button_style') || 'glass');
  const cycleBtnStyle = () => {
    const styles = ['glass', 'phosphor', 'minimal'];
    const next = styles[(styles.indexOf(btnStyle) + 1) % styles.length];
    localStorage.setItem('wc3_button_style', next);
    setBtnStyle(next);
    window.dispatchEvent(new Event('wc3-button-style-changed'));
  };

  const orderedWindows = useMemo(() => [...windows].sort((a, b) => a.openedAt - b.openedAt), [windows]);

  return (
    <div className="sticky top-0 z-200 flex items-center gap-4 border-b border-slate-200 bg-white/95 px-4 py-2 text-sm text-slate-900 shadow-md backdrop-blur">
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
        <HelpMenu />
        <TaskManagerIndicator />
        <button
          onClick={() => setShowInventoryMonitor((v) => !v)}
          className={`flex h-8 w-8 items-center justify-center rounded-full border transition ${
            showInventoryMonitor
              ? "border-emerald-300 bg-emerald-50 text-emerald-600"
              : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-emerald-500"
          }`}
          title="Inventory Monitor"
          aria-label="Inventory Monitor"
        >
          <FaBoxes className="h-4 w-4" />
        </button>
        {showInventoryMonitor && (
          <InventoryMonitor onClose={() => setShowInventoryMonitor(false)} />
        )}
        <button
          onClick={() => { const v = detailView === 'app' ? 'admin' : 'app'; localStorage.setItem('wc3_detail_view_pref', v); setDetailView(v); }}
          className={`flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-semibold transition ${
            detailView === 'admin'
              ? "border-purple-300 bg-purple-50 text-purple-700"
              : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"
          }`}
          title={detailView === 'app' ? "App pages — click for Admin/DataBrowser" : "Admin/DataBrowser — click for App pages"}
        >
          {detailView === 'app' ? 'App' : 'Admin'}
        </button>
        <button
          onClick={cycleBtnStyle}
          className={`flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-semibold transition ${
            btnStyle === 'glass' ? "border-amber-300 bg-amber-50 text-amber-700"
              : btnStyle === 'phosphor' ? "border-blue-300 bg-blue-50 text-blue-700"
              : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"
          }`}
          title={`Button style: ${btnStyle} — click to cycle (glass → phosphor → minimal)`}
        >
          {btnStyle === 'glass' ? '🔘 Glass' : btnStyle === 'phosphor' ? '◆ Duo' : '— Min'}
        </button>
        <div className="flex items-center gap-3 rounded-full bg-slate-100 px-2 py-1">
          <img
            src="/images/user/owner.jpg"
            alt="avatar"
            className="h-7 w-7 rounded-full border border-white object-cover"
          />
          <div className="leading-tight text-slate-800">
            <p className="text-[11px] text-slate-500">{user?.email || "user"}</p>
            <p className="text-xs font-semibold">{user?.name_first || "Profile"}</p>
          </div>
          <button
            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-70"
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
            title="Sign out"
            aria-label="Sign out"
            disabled={loggingOut}
          >
            <FiLogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}