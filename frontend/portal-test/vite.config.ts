import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [vue()],
  server: {
    host: '127.0.0.1', port: 5195, strictPort: true,
    fs: { allow: [fileURLToPath(new URL('..', import.meta.url))] },
    proxy: {
      '/operations-api': { target: 'http://127.0.0.1:8016', rewrite: path => path.replace('/operations-api/v1/', '/api/v1/') },
      '/__portal_test__': 'http://127.0.0.1:8016',
    },
  },
});
