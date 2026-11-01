<script setup lang="ts">
import AppIcon from './AppIcon.vue';
withDefaults(defineProps<{ detail?: boolean }>(), { detail: false });
</script>
<template>
  <div class="shell-notice">
    <AppIcon name="Info" :size="16" /><span
      ><strong>{{ detail ? '详情结构预览' : 'M0.5 界面预览' }}</strong
      ><span class="notice-divider">·</span
      >{{ detail ? '非业务记录，所有资料待接入' : '业务服务尚未接入，当前无工厂与业务数据' }}</span
    >
  </div>
</template>
