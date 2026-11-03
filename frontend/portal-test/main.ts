// Test host only; the real monitoring shell is checked separately in its repo.
import { createApp } from 'vue';
import { createRouter, createWebHistory, RouterView } from 'vue-router';
import { createOperationsRoutes } from '../src/integrations/monitor';
const router = createRouter({ history: createWebHistory(), routes: createOperationsRoutes() });
createApp(RouterView).use(router).mount('#app');
