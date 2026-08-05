/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useEffect, useState } from "react";
import { Provider } from "react-redux";
import { store } from "./store";
import AuthInitializer from "./components/common/AuthInitializer";
import { WindowManagerProvider } from "./context/WindowManagerContext";
import { StaffBadgePrefsProvider } from "./context/StaffBadgePrefsContext";
import Router from "./routes/Router";
import { DataSetBadge } from './components/DataSetBadge';
import { DevTools } from './components/DevTools';
import { AiHelpWidget } from './components/AiHelpWidget';
import { UserIssueReporter } from './components/UserIssueReporter';
import { DevIssueReporter } from './components/DevIssueReporter';
import { useDefaultCompany } from './hooks/useDefaultCompany';
import { AliceProvider } from './contexts/AliceContext';

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
      <Provider store={store}>
        <AliceProvider>
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
              <Router />
              {/* Floating widgets — hidden on public tool pages */}
              {!window.location.pathname.startsWith('/json-tree') && <>
                {/* Fixed position badge with expandable details */}
                <DataSetBadge position="bottom-right" showDetails />
                {/* Dev tools panel (only shows in DEV mode) */}
                <DevTools position="bottom-left" />
                {/* AI Help Assistant chat widget */}
                <AiHelpWidget position="bottom-right" />
                {/* Issue reporters — floating buttons for users & devs */}
                <UserIssueReporter />
                <DevIssueReporter />
              </>}
            </div>
          </StaffBadgePrefsProvider>
        </WindowManagerProvider>
        </AliceProvider>
      </Provider>
    </>
  );
}
