import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import svgr from "vite-plugin-svgr";
// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),tailwindcss(),svgr({
    svgrOptions: {
      icon: true,
      // This will transform your SVG to a React component
      exportType: "named",
      namedExport: "ReactComponent",
    },
  }),],
  // server: {
  //   host: '192.168.1.6',
  //   port: 5173
  // }
})

