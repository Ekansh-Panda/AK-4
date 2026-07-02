import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// https://vitejs.dev/config/
//
// This is the Miori remote dashboard — a phone-first web app served on the LAN
// so a person can reach the Miori host machine from their pocket. `server.host`
// is `true` so the dev server binds to 0.0.0.0 and is reachable from a phone on
// the same network (e.g. http://<host-lan-ip>:5174).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Relative base so the build can be hosted under any path the core-api decides
  // to mount it at (e.g. served behind the FastAPI app at /remote).
  base: "./",
  server: {
    host: true, // bind to all interfaces for LAN access from a phone
    port: 5174,
    strictPort: false,
  },
  preview: {
    host: true,
    port: 5174,
  },
  envPrefix: ["VITE_"],
  build: {
    target: "es2021",
    minify: "esbuild",
    sourcemap: false,
  },
});
