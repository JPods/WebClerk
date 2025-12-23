import { Provider } from "react-redux";
import { store } from "./store";
import Router from "./routes/Router";

export default function App() {
  return (
    <>
      <Provider store={store}>
        <div className="min-h-screen bg-[#F5F5F5] dark:bg-gray-900 bg-cust-default-body">
          <Router />
        </div>
      </Provider>
    </>
  );
}
