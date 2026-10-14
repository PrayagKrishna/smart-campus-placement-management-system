import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base URL is proxied in development, so the browser never needs to
// know the backend host and no credential is ever shipped to the client.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
