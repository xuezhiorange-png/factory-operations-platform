import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { isMonitorPortal } from '../api-path';

export function useShell() {
  const route = useRoute();
  const isMobile = computed(() => route.meta.shell === 'mobile');
  const pathFor = (path: string) => `${isMonitorPortal() ? '/operations' : isMobile.value ? '/m' : ''}/${path}`;
  return { isMobile, pathFor };
}
