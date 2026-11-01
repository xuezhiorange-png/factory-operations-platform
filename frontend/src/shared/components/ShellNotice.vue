<script setup lang="ts">
import { assetsApiEnabled } from '../../app/features';
import AppIcon from './AppIcon.vue';
withDefaults(defineProps<{ detail?: boolean }>(), { detail: false });
</script>
<template>
  <div class="shell-notice">
    <AppIcon name="Info" :size="16" /><span
      ><strong>{{
        detail ? '详情结构预览' : assetsApiEnabled ? 'M1-01 设备查询能力' : 'M0.5 界面预览'
      }}</strong
      ><span class="notice-divider">·</span
      >{{
        detail
          ? '非业务记录，所有资料待接入'
          : assetsApiEnabled
            ? '设备查询需后端会话与工厂授权，其他模块仍为空壳'
            : '业务服务尚未接入，当前无工厂与业务数据'
      }}</span
    >
  </div>
</template>
