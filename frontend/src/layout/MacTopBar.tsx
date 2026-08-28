/* LastChecked: 2026-08-16 | WhereUsed: Main layout top bar | Source: config.ui */
import { useMemo, useState, useCallback } from "react";
import { getUI, setUI } from "@/utils/contactUI";

/** Detail view preference from config.ui */
export function getDetailViewPref(): 'app' | 'admin' {
  return getUI<'app' | 'admin'>('detail.default_view', 'app');
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

export default function MacTopBar({ activePath }: Props) {
  const { windows, closeWindow, activateWindow } = useWindowManager();
  const { user } = useAppSelector((state) => state.auth);
  const apiBusy = useAppSelector((state) => state.loading.isApiLoading);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const [detailView, setDetailView] = useState<'app' | 'admin'>(() => getDetailViewPref());

  const orderedWindows = useMemo(() => [...windows].sort((a, b) => a.openedAt - b.openedAt), [windows]);
  const refreshExpires = useAppSelector((state) => state.auth.refreshExpires);

  const sessionWarning = useMemo(() => {
    if (!refreshExpires) return null;
    const exp = new Date(refreshExpires).getTime();
    const now = Date.now();
    const daysLeft = (exp - now) / (1000 * 60 * 60 * 24);
    if (daysLeft > 3 || daysLeft < 0) return null;
    const label = daysLeft < 1
      ? `${Math.max(0, Math.round(daysLeft * 24))}h`
      : `${Math.round(daysLeft)}d`;
    return label;
  }, [refreshExpires]);

  const handleReauth = useCallback(() => {
    navigate("/login");
  }, [navigate]);

  return (
    <div
      data-wc="mac-top-bar"
      className="sticky top-0 z-200 flex items-center gap-4 border-b px-4 text-sm backdrop-blur"
      style={{
        height: 40,
        backgroundColor: 'var(--wc-topbar-bg)',
        borderColor: 'var(--wc-topbar-border)',
        color: 'var(--wc-topbar-text)',
      }}
      data-zone="TopBar | .sticky.top-0 | MacTopBar.tsx"
    >

      {/* Left: Logo + window tabs */}
      <div className="flex items-center gap-2 text-sm font-semibold">
        <GridIcon className="h-4 w-4" style={{ color: 'var(--wc-accent-green)' }} />
        <span className="text-xs">WebClerk 3.0</span>
        {user?.prefs?.training && (
          <span className="rounded px-2 py-0.5 text-[9px] font-bold animate-pulse"
            style={{ backgroundColor: 'var(--wc-accent-red)', color: '#fff' }}>
            TRAINING
          </span>
        )}
        {apiBusy && (
          <span className="flex items-center gap-1 text-[9px]" style={{ color: 'var(--wc-accent)' }}>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full" style={{ backgroundColor: 'var(--wc-accent)' }} />
            Syncing
          </span>
        )}
        {sessionWarning && (
          <button
            onClick={handleReauth}
            className="flex items-center gap-1 rounded border px-2 py-0.5 text-[9px] font-medium transition"
            style={{
              backgroundColor: 'color-mix(in srgb, var(--wc-accent) 15%, transparent)',
              borderColor: 'var(--wc-accent)',
              color: 'var(--wc-topbar-text)',
            }}
            title="Your session expires soon. Click to sign in again."
          >
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: 'var(--wc-accent)' }} />
            Session expires in {sessionWarning}
          </button>
        )}
      </div>

      {/* Center: Window tabs */}
      <div className="flex flex-1 items-center gap-1.5 overflow-x-auto">
        {orderedWindows.map((w) => {
          const isActive = w.path === activePath;
          return (
            <div
              key={w.path}
              className="group flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] transition"
              style={{
                borderColor: isActive ? 'var(--wc-accent-green)' : 'var(--wc-topbar-border)',
                backgroundColor: isActive ? 'var(--wc-surface)' : 'var(--wc-surface-alt)',
                color: isActive ? 'var(--wc-topbar-text)' : 'var(--wc-topbar-text-muted)',
              }}
            >
              <span className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: isActive ? 'var(--wc-accent-green)' : 'var(--wc-text-dim)' }} />
              <button className="text-left" onClick={() => activateWindow(w.path)} title={w.path}>
                {w.title}
              </button>
              {isActive && <span className="text-[9px] font-medium" style={{ color: 'var(--wc-accent-green)' }}>Active</span>}
              <button className="transition" onClick={() => closeWindow(w.path)} title="Close"
                style={{ color: 'var(--wc-text-dim)' }}
                onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--wc-topbar-text)')}
                onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--wc-text-dim)')}>x</button>
            </div>
          );
        })}
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-1.5">
        <HelpMenu />
        <TaskManagerIndicator />

        <select data-wc="select" className="topbar-ctl" title="App: business forms (ui.json) | Admin: field grid (db.json)" value={detailView}
          onChange={(e) => {
            const v = e.target.value as 'app' | 'admin';
            setUI('detail.default_view', v);
            setDetailView(v);
            window.dispatchEvent(new CustomEvent('wc3-view-pref-changed', { detail: { mode: v } }));
          }}
        >
          <option value="app">View: App</option>
          <option value="admin">View: Admin</option>
        </select>

        <select data-wc="select" className="topbar-ctl" title="Font size"
          defaultValue={String(getUI('theme.' + getUI('theme.active', 'dark') + '.font.size', 14))}
          onChange={(e) => {
            const size = Number(e.target.value);
            const active = getUI('theme.active', 'dark');
            setUI(`theme.${active}.font.size`, size);
            window.dispatchEvent(new CustomEvent('wc3-font-size-changed', { detail: { size } }));
          }}
        >
          <option value="10">Font: 10</option>
          <option value="12">Font: 12</option>
          <option value="14">Font: 14</option>
          <option value="16">Font: 16</option>
          <option value="18">Font: 18</option>
        </select>

        <select data-wc="select" className="topbar-ctl" title="Color mode"
          defaultValue=""
          onChange={(e) => {
            const mode = e.target.value as 'dark' | 'light';
            if (!mode) return;
            setUI('theme.active', mode);
            window.dispatchEvent(new CustomEvent('wc3-zone-theme-changed', { detail: { zone: 'all', mode } }));
            e.target.value = '';
          }}
        >
          <option value="">Theme...</option>
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </select>

        {/* User — avatar + name + sign out */}
        <div className="flex items-center gap-1.5 pl-1.5 border-l" style={{ borderColor: 'var(--wc-topbar-border)' }}>
          <img src="/images/user/owner.jpg" alt="avatar" className="h-5 w-5 rounded-full border border-white object-cover cursor-pointer"
            onDoubleClick={() => { if (user?.id) { sessionStorage.setItem('db_auto_select', String(user.id)); navigate(`/contact`); } }}
            title="Double-click to open your contact record" />
          <span className="text-[10px] font-medium cursor-pointer" style={{ color: 'var(--wc-topbar-text-muted)' }}
            onDoubleClick={() => { if (user?.id) { sessionStorage.setItem('db_auto_select', String(user.id)); navigate(`/contact`); } }}
            title="Double-click to open your contact record">{user?.name_first || "Profile"}</span>
          <button
            className="flex h-5 w-5 items-center justify-center rounded-full transition"
            style={{ color: 'var(--wc-text-dim)' }}
            onClick={async () => {
              if (loggingOut) return;
              setLoggingOut(true);
              try { await logoutRequest(); } catch {}
              clearTokens();
              dispatch(clearUser());
              navigate("/login");
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
