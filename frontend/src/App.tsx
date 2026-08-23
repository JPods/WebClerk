/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { Provider } from "react-redux";
import { store } from "./store";
import AuthInitializer from "./components/common/AuthInitializer";
import { WindowManagerProvider } from "./context/WindowManagerContext";
import { StaffBadgePrefsProvider } from "./context/StaffBadgePrefsContext";
import Router from "./routes/Router";
import { useDefaultCompany } from './hooks/useDefaultCompany';
import { AliceProvider } from './context/AliceContext';
import { PermissionsProvider } from './context/PermissionsContext';
import { SettingsBootstrap } from './components/SettingsBootstrap';
import ErrorBoundary from './components/common/ErrorBoundary';

function PrimeCompanyBootstrap() {
  useDefaultCompany();

  return null;
}

export default function App() {
  const [smallScreenDismissed, setSmallScreenDismissed] = useState(false);
  const [isSmallScreen, setIsSmallScreen] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia("(max-width: 767px)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setIsSmallScreen(media.matches);
    media.addEventListener("change", update);
    update();
    return () => media.removeEventListener("change", update);
  }, []);

  return (
    <>
      <SettingsBootstrap>
      <Provider store={store}>
        <AliceProvider>
        <PermissionsProvider>
        <WindowManagerProvider>
          <StaffBadgePrefsProvider>
            <AuthInitializer />
            <PrimeCompanyBootstrap />
            <div className="min-h-screen bg-slate-50 text-slate-900">
              {isSmallScreen && !smallScreenDismissed && (
                <div className="fixed inset-x-0 top-0 z-50 flex items-center justify-between bg-amber-50 px-4 py-2 text-sm text-amber-800 shadow-sm">
                  <span>Your screen is small — some features may be hard to use.</span>
                  <button
                    onClick={() => setSmallScreenDismissed(true)}
                    className="ml-4 rounded bg-amber-200 px-2 py-0.5 text-xs font-medium hover:bg-amber-300"
                  >
                    Dismiss
                  </button>
                </div>
              )}
              <ErrorBoundary>
                <Router />
              </ErrorBoundary>
            </div>
          </StaffBadgePrefsProvider>
        </WindowManagerProvider>
        </PermissionsProvider>
        </AliceProvider>
      </Provider>
      </SettingsBootstrap>
    </>
  );
}
