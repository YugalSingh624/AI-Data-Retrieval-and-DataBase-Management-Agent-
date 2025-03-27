// File: vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://localhost:5000', // Your Flask backend address
        changeOrigin: true,
        secure: false,
      }
    },
    port: 3000
  }
});