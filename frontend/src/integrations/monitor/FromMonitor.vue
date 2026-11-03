<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import EmptyState from '../../shared/components/EmptyState.vue';
import { readLink } from './links';
const route = useRoute(), router = useRouter();
const title = ref('正在检查设备关联…');
let controller: AbortController | undefined;
watch(() => route.fullPath, async () => {
  controller?.abort();
  const current = new AbortController(); controller = current;
  title.value = '正在检查设备关联…';
  const factory = route.query.monitor_factory_id, device = route.query.monitor_device_id;
  if (typeof factory !== 'string' || typeof device !== 'string') { title.value = '尚未关联'; return; }
  try {
    const link = await readLink('resolve', { monitor_factory_id: factory, monitor_device_id: device }, current.signal);
    if (current.signal.aborted) return;
    if (link) await router.replace({ path: `/operations/assets/${link.asset_id}`, query: { factory: link.factory_id } });
    else title.value = '尚未关联';
  } catch { if (!current.signal.aborted) title.value = '关联查询失败或无访问权限'; }
}, { immediate: true });
onUnmounted(() => controller?.abort());
</script>
<template><EmptyState :title="title" description="仅展示已确认 ID 映射且在授权工厂范围内的设备。" icon="Boxes" /></template>
