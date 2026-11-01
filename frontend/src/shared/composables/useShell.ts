import { computed } from 'vue';
import { useRoute } from 'vue-router';

export function useShell() {
  const route = useRoute();
  const isMobile = computed(() => route.meta.shell === 'mobile');
  const pathFor = (path: string) => `${isMobile.value ? '/m' : ''}/${path}`;
  return { isMobile, pathFor };
}
