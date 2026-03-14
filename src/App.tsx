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

function PrimeCompanyBootstrap() {
  useDefaultCompany();

  return null;
}

export default function App() {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia("(max-width: 767px)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(media.matches);
    media.addEventListener("change", update);
    update();
    return () => media.removeEventListener("change", update);
  }, []);

  if (isMobile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-center text-slate-800 dark:bg-slate-900 dark:text-slate-100">
        <div className="max-w-sm space-y-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-md dark:border-slate-800 dark:bg-slate-900/70">
          <p className="text-sm font-semibold tracking-wide text-indigo-600 dark:text-indigo-300">Desktop Only</p>
          <p className="text-lg font-semibold">Open on a larger screen</p>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            This workspace is optimized for tablets and desktops. Please continue on a device with a wider screen.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <Provider store={store}>
        <WindowManagerProvider>
          <StaffBadgePrefsProvider>
            <AuthInitializer />
            <PrimeCompanyBootstrap />
            <div className="min-h-screen bg-slate-50 text-slate-900">
              <Router />
              {/* Fixed position badge with expandable details */}
              <DataSetBadge position="bottom-right" showDetails />
              {/* Dev tools panel (only shows in DEV mode) */}
              <DevTools position="bottom-left" />
              {/* AI Help Assistant chat widget */}
              <AiHelpWidget position="bottom-right" />
              {/* Issue reporters — floating buttons for users & devs */}
              <UserIssueReporter />
              <DevIssueReporter />
            </div>
          </StaffBadgePrefsProvider>
        </WindowManagerProvider>
      </Provider>
    </>
  );
}
