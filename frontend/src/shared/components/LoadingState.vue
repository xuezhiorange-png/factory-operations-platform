<script setup lang="ts">
import AppIcon from './AppIcon.vue';
</script>
<template>
  <div class="loading-state" role="status" aria-busy="true">
    <AppIcon name="LoaderCircle" class="spin" /><span>加载状态展示 · 未请求业务数据</span>
    <div class="skeleton-lines" aria-hidden="true"><i></i><i></i><i></i></div>
  </div>
</template>
