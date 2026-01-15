import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "swiper/swiper-bundle.css";
import "flatpickr/dist/flatpickr.css";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";

// Data Set Identification - startup notice
const dataSetId = import.meta.env.VITE_DATA_SET_ID || 'UNKNOWN';
const dataSetName = import.meta.env.VITE_DATA_SET_NAME || 'Unknown';
const env = import.meta.env.VITE_ENV || 'DEV';
console.log(
  `%c[React2025] Data Set: ${dataSetId} - ${dataSetName} (${env})`,
  'color: #22c55e; font-weight: bold; font-size: 14px;'
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AppWrapper>
        <App />
      </AppWrapper>
    </ThemeProvider>
  </StrictMode>
);
