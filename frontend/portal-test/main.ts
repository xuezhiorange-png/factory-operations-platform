// Test host only; the real monitoring shell is checked separately in its repo.
import { createApp } from 'vue';
import { createRouter, createWebHistory, RouterView } from 'vue-router';
import { createOperationsRoutes } from '../src/integrations/monitor';
const connected = new URLSearchParams(location.search).get('connected') !== 'false';
const router = createRouter({ history: createWebHistory(), routes: createOperationsRoutes({ connected }) });
createApp(RouterView).use(router).mount('#app');
