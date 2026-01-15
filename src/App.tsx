import { Provider } from "react-redux";
import { store } from "./store";
import AuthInitializer from "./components/common/AuthInitializer";
import { WindowManagerProvider } from "./context/WindowManagerContext";
import Router from "./routes/Router";
import { DataSetBadge } from './components/DataSetBadge';

export default function App() {
  return (
    <>
      <Provider store={store}>
        <WindowManagerProvider>
          <AuthInitializer />
          <div className="min-h-screen bg-slate-50 text-slate-900">
            <Router />
            {/* Fixed position badge with expandable details */}
            <DataSetBadge position="bottom-right" showDetails />
          </div>
        </WindowManagerProvider>
      </Provider>
    </>
  );
}
