import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { readFileSync } from 'node:fs';

export default defineConfig({
  plugins: [vue()],
  preview: {
    https:
      process.env.FACTORY_OPS_TEST_TLS_KEY && process.env.FACTORY_OPS_TEST_TLS_CERT
        ? {
            key: readFileSync(process.env.FACTORY_OPS_TEST_TLS_KEY),
            cert: readFileSync(process.env.FACTORY_OPS_TEST_TLS_CERT),
          }
        : undefined,
    proxy: {
      '/api': {
        target: process.env.FACTORY_OPS_API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
