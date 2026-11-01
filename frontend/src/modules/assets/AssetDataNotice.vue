<script setup lang="ts">
import AppIcon from '../../shared/components/AppIcon.vue';
import type { DataSource } from './contracts';
defineProps<{ source?: DataSource }>();
</script>
<template>
  <div class="shell-notice" :class="{ 'synthetic-notice': source === 'synthetic_test' }">
    <AppIcon name="Info" :size="16" /><span
      ><strong>{{
        source === 'synthetic_test' ? '隔离测试环境 · 合成数据' : 'M1-01 设备只读查询'
      }}</strong
      ><span class="notice-divider">·</span
      >{{
        source === 'synthetic_test'
          ? '以下记录来自隔离 PostgreSQL，不是生产设备数据'
          : '新增、编辑、附件与其他业务仍未接入'
      }}</span
    >
  </div>
</template>
