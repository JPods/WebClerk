import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "swiper/swiper-bundle.css";
import "flatpickr/dist/flatpickr.css";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";
import { SaveQueueProvider } from "./context/SaveQueueContext.tsx";
import { RequestQueueProvider } from "./context/RequestQueueContext.tsx";

// Data Set Identification - startup notice
const dataSetId = import.meta.env.VITE_DATA_SET_ID || "UNKNOWN";
const dataSetName = import.meta.env.VITE_DATA_SET_NAME || "Unknown";
const env = import.meta.env.VITE_ENV || "DEV";

console.log(
  `%c[React2025] Frontend: ${dataSetId} - ${dataSetName} (${env})`,
  "color: #22c55e; font-weight: bold; font-size: 14px;",
);

// Fetch and display backend database mode (optional - endpoint may not exist)
fetch("/wcapi/dev/config/")
  .then((res) => (res.ok ? res.json() : null))
  .then((data) => {
    const configData = data?.data?.data || data?.data;
    if (configData?.db_mode) {
      const mode = configData.db_mode.toUpperCase();
      const color = mode === "REMOTE" ? "#22c55e" : "#3b82f6";
      console.log(
        `%c[React2025] Backend DB: ${mode} database`,
        `color: ${color}; font-weight: bold; font-size: 14px;`,
      );
    }
  })
  .catch(() => {
    /* Backend dev config not available - expected in production */
  });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <RequestQueueProvider>
        <SaveQueueProvider>
          <AppWrapper>
            <App />
          </AppWrapper>
        </SaveQueueProvider>
      </RequestQueueProvider>
    </ThemeProvider>
  </StrictMode>,
);
