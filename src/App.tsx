import { Provider } from "react-redux";
import { store } from "./store";
import GlobalLoadingSpinner from "./components/common/GlobalLoadingSpinner";
import Router from "./routes/Router";

export default function App() {
  return (
    <>
      <Provider store={store}>
        <div className="min-h-screen bg-[#f1f0ff] dark:bg-gray-900 ">
          <Router />
          <GlobalLoadingSpinner />
        </div>
      </Provider>
    </>
  );
}
