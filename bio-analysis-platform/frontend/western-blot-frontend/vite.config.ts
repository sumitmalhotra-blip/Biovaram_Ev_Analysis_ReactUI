import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: './',   // relative paths so assets load correctly under file:// in Electron
  server: {
    proxy: {
      '/tem':     'http://127.0.0.1:8000',
      '/western': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000',
      '/results': 'http://127.0.0.1:8000',
      '/health':  'http://127.0.0.1:8000',
    },
  },
});