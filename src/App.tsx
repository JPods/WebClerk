import { Provider } from "react-redux";
import { store } from "./store";
import AuthInitializer from "./components/common/AuthInitializer";
import { WindowManagerProvider } from "./context/WindowManagerContext";
import Router from "./routes/Router";

export default function App() {
  return (
    <>
      <Provider store={store}>
        <WindowManagerProvider>
          <AuthInitializer />
          <div className="min-h-screen bg-slate-50 text-slate-900">
            <Router />
          </div>
        </WindowManagerProvider>
      </Provider>
    </>
  );
}
