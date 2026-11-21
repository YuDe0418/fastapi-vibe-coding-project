import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import process from 'node:process';
import { fileURLToPath, URL } from 'node:url';

const backendPort = process.env.COMMON_GROUND_BACKEND_PORT ?? '8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: `http://127.0.0.1:${backendPort}`, changeOrigin: false } },
  },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts', css: false },
});
