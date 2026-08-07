/* LastChecked: 2026-08-04 | WhereUsed: Main layout top bar | WhoCreated: Unknown */
import { useMemo, useState } from "react";

/** Detail view preference — "app" = .tsx pages, "admin" = DataBrowser detail */
export function getDetailViewPref(): 'app' | 'admin' {
  return (localStorage.getItem('wc3_detail_view_pref') as 'app' | 'admin') || 'app';
}
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { FiLogOut } from "react-icons/fi";
import { GridIcon } from "../icons";
import { useWindowManager } from "../context/WindowManagerContext";
import { logout as logoutRequest } from "../api/auth";
import { useAppSelector } from "../store/hooks";
import { clearTokens } from "../api/axios";
import { clearUser } from "../store/slices/authSlice";
import TaskManagerIndicator from "../components/header/TaskManagerIndicator";
import HelpMenu from "../components/common/HelpMenu";

type Props = {
  activePath: string;
};

// Shared select/button style — all TopBar controls match
const ctlClass = "rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-slate-600 hover:border-slate-300 transition cursor-pointer";

export default function MacTopBar({ activePath }: Props) {
  const { windows, closeWindow, activateWindow } = useWindowManager();
  const { user } = useAppSelector((state) => state.auth);
  const apiBusy = useAppSelector((state) => state.loading.isApiLoading);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const [detailView, setDetailView] = useState<'app' | 'admin'>(() => getDetailViewPref());

  const orderedWindows = useMemo(() => [...windows].sort((a, b) => a.openedAt - b.openedAt), [windows]);

  return (
    <div className="sticky top-0 z-200 flex items-center gap-4 border-b border-slate-200 bg-white/95 px-4 text-sm text-slate-900 backdrop-blur" style={{ height: 40 }} data-zone="TopBar | .sticky.top-0 | MacTopBar.tsx">

      {/* ═══ Left: Logo + window tabs ═══ */}
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <GridIcon className="h-4 w-4 text-emerald-500" />
        <span className="text-xs">WebClerk 3.0</span>
        {user?.prefs?.training && (
          <span className="rounded bg-red-600 px-2 py-0.5 text-[9px] font-bold text-white animate-pulse">
            TRAINING
          </span>
        )}
        {apiBusy && (
          <span className="flex items-center gap-1 text-[9px] text-amber-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
            Syncing
          </span>
        )}
      </div>

      {/* ═══ Center: Window tabs ═══ */}
      <div className="flex flex-1 items-center gap-1.5 overflow-x-auto">
        {orderedWindows.map((w) => {
          const isActive = w.path === activePath;
          return (
            <div
              key={w.path}
              className={`group flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] transition ${
                isActive
                  ? "border-emerald-300 bg-white text-slate-900 shadow-sm"
                  : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-white"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${isActive ? "bg-emerald-500" : "bg-slate-300"}`} />
              <button className="text-left" onClick={() => activateWindow(w.path)} title={w.path}>
                {w.title}
              </button>
              {isActive && <span className="text-[9px] font-medium text-emerald-600">Active</span>}
              <button className="text-slate-400 hover:text-slate-700" onClick={() => closeWindow(w.path)} title="Close">x</button>
            </div>
          );
        })}
      </div>

      {/* ═══ Right: Controls — all same size ═══ */}
      <div className="flex items-center gap-1.5">
        <HelpMenu />

        {/* Stale pending indicator — only shows after 10 minutes */}
        <TaskManagerIndicator />

        <select className={ctlClass} title="Detail view mode" value={detailView}
          onChange={(e) => {
            const v = e.target.value as 'app' | 'admin';
            localStorage.setItem('wc3_detail_view_pref', v);
            setDetailView(v);
            window.dispatchEvent(new CustomEvent('wc3-view-pref-changed', { detail: { mode: v } }));
          }}
        >
          <option value="app">View: App</option>
          <option value="admin">View: Admin</option>
        </select>

        <select className={ctlClass} title="Font size"
          defaultValue={(() => { try { const p = JSON.parse(localStorage.getItem('wc3_wcui_prefs') || '{}'); return String(p.font_size || 12); } catch { return '12'; } })()}
          onChange={(e) => {
            const size = Number(e.target.value);
            window.dispatchEvent(new CustomEvent('wc3-font-size-changed', { detail: { size } }));
          }}
        >
          <option value="10">Font: 10</option>
          <option value="12">Font: 12</option>
          <option value="14">Font: 14</option>
          <option value="16">Font: 16</option>
          <option value="18">Font: 18</option>
        </select>

        <select className={ctlClass} title="Color mode: list/detail — saves to your prefs"
          defaultValue=""
          onChange={async (e) => {
            const [zone, mode] = e.target.value.split(':');
            if (!zone || !mode) return;
            window.dispatchEvent(new CustomEvent('wc3-zone-theme-changed', { detail: { zone, mode } }));
            try {
              const { saveRecord } = await import('@/api/wcapi');
              const userId = user?.id;
              if (userId) {
                const currentPrefs = (user as any)?.prefs || {};
                const staff = currentPrefs.staff || {};
                const colorMode = staff.color_mode || currentPrefs.color_mode || {};
                colorMode[zone] = mode;
                staff.color_mode = colorMode;
                await saveRecord('contact', { id: userId, prefs: { ...currentPrefs, staff } });
              }
            } catch (err) { console.error('Failed to save color_mode pref:', err); }
            e.target.value = '';
          }}
        >
          <option value="">Theme...</option>
          <option value="list:dark">List: Dark</option>
          <option value="list:light">List: Light</option>
          <option value="detail:dark">Detail: Dark</option>
          <option value="detail:light">Detail: Light</option>
        </select>

        <button className={ctlClass} title="Save current UI settings to your preferences"
          onClick={async () => {
            try {
              const { saveRecord } = await import('@/api/wcapi');
              const userId = user?.id;
              if (!userId) return;
              const currentPrefs = (user as any)?.prefs || {};
              const staff = currentPrefs.staff || {};

              staff.wcui = {
                ...(staff.wcui || {}),
                view_mode: localStorage.getItem('wc3_detail_view_pref') || 'app',
                font_size: (() => { try { return JSON.parse(localStorage.getItem('wc3_wcui_prefs') || '{}').font_size || 12; } catch { return 12; } })(),
                theme: localStorage.getItem('db-theme') || 'dark',
              };

              await saveRecord('contact', { id: userId, prefs: { ...currentPrefs, staff } });
            } catch (err) {
              console.error('Failed to save prefs:', err);
            }
          }}
        >
          Save Prefs
        </button>

        {/* User — avatar + name + sign out */}
        <div className="flex items-center gap-1.5 pl-1.5 border-l border-slate-200">
          <img src="/images/user/owner.jpg" alt="avatar" className="h-5 w-5 rounded-full border border-white object-cover" />
          <span className="text-[10px] font-medium text-slate-600">{user?.name_first || "Profile"}</span>
          <button
            className="flex h-5 w-5 items-center justify-center rounded-full text-slate-400 hover:text-slate-700 transition"
            onClick={async () => {
              if (loggingOut) return;
              setLoggingOut(true);
              try { await logoutRequest(); } catch {}
              clearTokens();
              dispatch(clearUser());
              navigate("/");
              setLoggingOut(false);
            }}
            title="Sign out"
            aria-label="Sign out"
            disabled={loggingOut}
          >
            <FiLogOut className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
