import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend so there are no CORS issues
// during local development. In production the frontend is served as static
// files behind the same domain (see DEPLOYMENT.md).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
  build: { outDir: "dist", chunkSizeWarningLimit: 1500 },
});
