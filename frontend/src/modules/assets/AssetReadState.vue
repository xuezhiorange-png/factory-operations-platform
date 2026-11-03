<script setup lang="ts">
import AppIcon from '../../shared/components/AppIcon.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
import { useRoute } from 'vue-router';
import { loginTarget } from '../identity/account';
import { isMonitorPortal } from '../../shared/api-path';
const route = useRoute();
export type ReadState =
  | 'loading'
  | 'loaded'
  | 'empty'
  | 'error'
  | 'forbidden'
  | 'not-found'
  | 'expired';
defineProps<{ state: ReadState }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div v-if="state === 'loading'" class="loading-state" role="status" aria-busy="true">
    <AppIcon name="LoaderCircle" class="spin" /><span>正在查询设备数据…</span>
  </div>
  <EmptyState
    v-else-if="state === 'expired' && !isMonitorPortal()"
    icon="ShieldCheck"
    title="登录已过期"
    description="平台会话已过期或被撤销，请重新登录后查询。"
    ><RouterLink
      class="button primary"
      :to="{
        path: loginTarget(route.path),
        query: { return_to: route.fullPath, status: 'expired' },
      }"
      >重新登录</RouterLink
    ></EmptyState
  >
  <EmptyState
    v-else-if="state === 'forbidden' || state === 'expired'"
    icon="ShieldCheck"
    title="无查询权限"
    description="需要有效的平台会话与工厂授权。当前不会显示其他工厂的数据，也不提供模拟登录。"
    ><button class="button secondary" @click="$emit('retry')">重新检查权限</button></EmptyState
  >
  <EmptyState
    v-else-if="state === 'error'"
    icon="Unplug"
    title="设备查询失败"
    description="服务暂不可用或响应无效，请稍后重试。"
    ><button class="button secondary" @click="$emit('retry')">重试查询</button></EmptyState
  >
  <EmptyState
    v-else-if="state === 'not-found'"
    icon="Search"
    title="没有可访问的设备"
    description="未找到对应工厂范围内的设备记录。"
  />
  <EmptyState
    v-else-if="state === 'empty'"
    icon="Boxes"
    title="暂无设备数据"
    description="查询已完成，当前工厂或筛选条件下没有设备记录。"
  />
</template>
