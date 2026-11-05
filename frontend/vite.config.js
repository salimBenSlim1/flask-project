import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, Vite proxies /api -> Flask (same idea as nginx in Docker), so the browser
// only ever talks to one origin and CORS never comes into play.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    proxy: {
      "/api": process.env.VITE_API_TARGET || "http://localhost:5000",
    },
  },
});
