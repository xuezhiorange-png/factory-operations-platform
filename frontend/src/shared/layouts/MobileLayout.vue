<script setup lang="ts">
import { useRoute } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import type { IconName } from '../icons';
const route = useRoute();
const tabs: { path: string; label: string; icon: IconName; key: string }[] = [
  { path: '/m/home', label: '首页', icon: 'Home', key: 'home' },
  { path: '/m/tasks', label: '任务', icon: 'ClipboardList', key: 'tasks' },
  { path: '/m/scan', label: '扫码', icon: 'QrCode', key: 'scan' },
  { path: '/m/messages', label: '消息', icon: 'Bell', key: 'messages' },
  { path: '/m/me', label: '我的', icon: 'CircleUserRound', key: 'me' },
];
function focusMain() {
  document.getElementById('main-content')?.focus();
}
</script>
<template>
  <div class="mobile-shell">
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">跳到主要内容</a>
    <header class="mobile-topbar">
      <RouterLink
        v-if="!['home', 'tasks', 'scan', 'messages', 'me'].includes(String(route.meta.mobilePage))"
        :to="route.meta.detail ? `/m/${route.meta.moduleId}` : '/m/home'"
        class="icon-button"
        aria-label="返回上级页面"
        ><AppIcon name="ArrowLeft" /></RouterLink
      ><RouterLink v-else to="/m/home" class="mobile-brand" aria-label="移动工作台首页"
        ><AppIcon name="Boxes" :size="23" /></RouterLink
      ><strong>{{ route.meta.title }}</strong
      ><RouterLink to="/m/messages" class="icon-button" aria-label="打开消息"
        ><AppIcon name="Bell" :size="21"
      /></RouterLink>
    </header>
    <main id="main-content" tabindex="-1" class="mobile-content">
      <RouterView :key="route.path" />
    </main>
    <nav class="mobile-bottom-nav" aria-label="移动端主导航">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.path"
        :class="{ active: route.meta.mobileTab === tab.key, 'scan-tab': tab.key === 'scan' }"
        :aria-current="route.meta.mobileTab === tab.key ? 'page' : undefined"
        ><span><AppIcon :name="tab.icon" :size="22" /></span
        ><small>{{ tab.label }}</small></RouterLink
      >
    </nav>
  </div>
</template>
