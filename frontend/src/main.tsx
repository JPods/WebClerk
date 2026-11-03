/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";
import { RequestQueueProvider } from "./context/RequestQueueContext.tsx";
// AliceProvider moved to App.tsx (inside Redux Provider)

// Console capture — Alice reads errors/warnings, feeds vectorstores
import { consoleCapture } from './utils/consoleCapture';
consoleCapture.start();
consoleCapture.startAutoFlush(60_000); // flush errors to Alice every 60s

// Data Set Identification - startup notice
const dataSetId = import.meta.env.VITE_DATA_SET_KIND || "live";
const dataSetName = import.meta.env.VITE_DATA_SET_NAME || "Unknown";
const env = import.meta.env.VITE_ENV || "DEV";

console.log(
  `%c[React2025] Frontend: ${dataSetId} - ${dataSetName} (${env})`,
  "color: #22c55e; font-weight: bold; font-size: 14px;",
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <RequestQueueProvider>
        <AppWrapper>
          <App />
        </AppWrapper>
      </RequestQueueProvider>
    </ThemeProvider>
  </StrictMode>,
);
