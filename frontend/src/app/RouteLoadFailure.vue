<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppIcon from '../shared/components/AppIcon.vue';
import { reloadFailedPage, returnToWorkspace } from './router';
const heading = ref<HTMLHeadingElement>();
onMounted(() => heading.value?.focus());
</script>
<template>
  <main class="route-failure panel">
    <section role="alert" aria-labelledby="route-failure-heading">
      <div class="connection-mark"><AppIcon name="Unplug" :size="28" /></div>
      <h1 id="route-failure-heading" ref="heading" tabindex="-1">页面暂时无法打开</h1>
      <p>页面资源加载失败。请检查网络连接后重新加载，或返回工作台继续浏览。</p>
      <p>页面尚未加载，没有执行任何业务操作。</p>
      <div class="route-failure-actions">
        <button class="button primary" @click="reloadFailedPage">重新加载页面</button>
        <button class="button secondary" @click="returnToWorkspace">返回工作台</button>
      </div>
    </section>
  </main>
</template>
