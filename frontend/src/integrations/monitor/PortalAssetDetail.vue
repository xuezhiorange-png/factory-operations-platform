<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import AssetLiveDetail from '../../modules/assets/AssetLiveDetail.vue';
import { detailConfig } from '../../modules/assets/config';
import { readLink, type MonitorLink } from './links';
const route = useRoute();
const link = ref<MonitorLink | null>();
const message = ref('正在检查监控关联…');
let controller: AbortController | undefined;
watch(() => route.fullPath, async () => {
  controller?.abort();
  const current = new AbortController(); controller = current;
  link.value = undefined; message.value = '正在检查监控关联…';
  try {
    const factory = typeof route.query.factory === 'string' ? route.query.factory : '';
    if (!factory) throw new Error('缺少工厂 ID');
    const result = await readLink('asset-link', { factory_id: factory, asset_id: String(route.params.id) }, current.signal);
    if (!current.signal.aborted) { link.value = result; message.value = result ? '已关联监控设备' : '尚未关联'; }
  } catch { if (!current.signal.aborted) message.value = '监控关联查询失败'; }
}, { immediate: true });
onUnmounted(() => controller?.abort());
</script>
<template><AssetLiveDetail :config="detailConfig"><template #monitor-link><div class="operations-monitor-link" role="status"><span>{{ message }}</span><RouterLink v-if="link" :to="{ path: '/devices', query: { ops_factory: link.factory_id, ops_asset: link.asset_id } }">查看监控状态</RouterLink></div></template></AssetLiveDetail></template>
