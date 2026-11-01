<script setup lang="ts">
import AppIcon from '../shared/components/AppIcon.vue';
import { useShell } from '../shared/composables/useShell';
const { isMobile } = useShell();
</script>
<template>
  <section class="not-found panel">
    <span class="eyebrow">PAGE NOT FOUND</span>
    <p class="not-found-code">404</p>
    <h1>这个页面不在工作空间中</h1>
    <p>请检查页面地址，或返回工作台继续浏览。</p>
    <RouterLink :to="isMobile ? '/m/home' : '/workbench'" class="button primary"
      >返回工作台<AppIcon name="ArrowRight" :size="17"
    /></RouterLink>
  </section>
</template>
