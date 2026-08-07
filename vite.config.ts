import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";
import { fileURLToPath } from "url";
import { loadEnv } from "vite";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Read backend DB_MODE from webClerk3/.env
function getBackendDbMode(): string {
  try {
    const backendEnvPath = path.resolve(__dirname, "../webClerk3/.env");
    if (fs.existsSync(backendEnvPath)) {
      const envContent = fs.readFileSync(backendEnvPath, "utf-8");
      const match = envContent.match(/^DB_MODE=(.+)$/m);
      if (match) return match[1].trim().toUpperCase();
    }
  } catch {
    /* ignore */
  }
  return "UNKNOWN";
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env to display in startup message
  const env = loadEnv(mode, process.cwd(), "");
  const dataSetId = env.VITE_DATA_SET_ID || "UNKNOWN";
  const dataSetName = env.VITE_DATA_SET_NAME || "Unknown";
  const dbMode = getBackendDbMode();
  const dbColor = dbMode === "REMOTE" ? "\x1b[32m" : "\x1b[34m"; // Green for remote, blue for local

  // Startup banner
  console.log("\n");
  console.log(
    "\x1b[36m%s\x1b[0m",
    "═══════════════════════════════════════════════════════",
  );
  console.log(
    "\x1b[36m%s\x1b[0m",
    `  [React2025] Data Set: ${dataSetId} - ${dataSetName}`,
  );
  console.log(`  [React2025] Database: ${dbColor}${dbMode}\x1b[0m`);
  console.log("\x1b[36m%s\x1b[0m", "  Proxying API to http://localhost:8000");
  console.log(
    "\x1b[36m%s\x1b[0m",
    "═══════════════════════════════════════════════════════",
  );
  console.log("\n");

  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [
      react(),
      svgr({
        svgrOptions: {
          icon: true,
          // This will transform your SVG to a React component
          exportType: "named",
          namedExport: "ReactComponent",
        },
      }),
    ],
    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-router-dom",
        "@excalidraw/excalidraw",
      ],
      exclude: ["@excalidraw/excalidraw/locales"],
    },
    resolve: {
      alias: [
        { find: "@", replacement: path.resolve(__dirname, "./src") },
        {
          find: /^react-data-table-component$/,
          replacement: path.resolve(
            __dirname,
            "./src/lib/reorderable-data-table.tsx",
          ),
        },
      ],
    },
    server: {
      proxy: {
        "/wcapi": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/communications": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/orgs/": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
        "/tx": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
