<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { navigation, navigationGroups } from '../../app/navigation';
import AppIcon from '../components/AppIcon.vue';
import AppOverlay from '../components/AppOverlay.vue';
import EmptyState from '../components/EmptyState.vue';
const route = useRoute();
const sidebarOpen = ref(false);
const searchOpen = ref(false);
const factoryOpen = ref(false);
const accountOpen = ref(false);
const query = ref('');
const pages = computed(() => navigation.filter((item) => item.title.includes(query.value.trim())));
watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false;
    searchOpen.value = false;
  },
);
function focusMain() {
  document.getElementById('main-content')?.focus();
}
</script>
<template>
  <div class="desktop-shell">
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">跳到主要内容</a>
    <button
      v-if="sidebarOpen"
      class="sidebar-backdrop"
      aria-label="关闭导航菜单"
      @click="sidebarOpen = false"
    ></button>
    <aside id="main-sidebar" class="sidebar" :class="{ expanded: sidebarOpen }">
      <RouterLink to="/workbench" class="brand"
        ><span class="brand-icon"><AppIcon name="Boxes" :size="25" /></span
        ><span><strong>工厂设备运维</strong><small>FACTORY OPERATIONS</small></span></RouterLink
      >
      <nav aria-label="主导航" class="sidebar-nav">
        <div v-for="group in navigationGroups" :key="group" class="nav-group">
          <p>{{ group }}</p>
          <RouterLink
            v-for="item in navigation.filter((item) => item.group === group)"
            :key="item.id"
            :to="`/${item.id}`"
            :class="{ active: route.meta.moduleId === item.id }"
            ><AppIcon :name="item.icon" :size="19" /><span>{{ item.title }}</span
            ><span v-if="route.meta.moduleId === item.id" class="nav-active-dot"></span
          ></RouterLink>
        </div>
      </nav>
      <div class="sidebar-footer">
        <RouterLink to="/m/home"
          ><AppIcon name="Smartphone" :size="18" /><span>移动工作台</span
          ><AppIcon name="ArrowUpRight" :size="15"
        /></RouterLink>
        <div class="sidebar-stage">
          <span class="status-dot"></span>M0.5 <span>平台框架预览</span>
        </div>
      </div>
    </aside>
    <div class="desktop-workspace">
      <header class="topbar">
        <button
          class="icon-button sidebar-toggle"
          aria-label="打开导航菜单"
          :aria-expanded="sidebarOpen"
          aria-controls="main-sidebar"
          @click="sidebarOpen = !sidebarOpen"
        >
          <AppIcon name="Menu" />
        </button>
        <div class="topbar-product">
          <span>运维管理</span><span class="topbar-label">管理端</span>
        </div>
        <div class="topbar-actions">
          <button class="topbar-search" aria-label="搜索页面" @click="searchOpen = true">
            <AppIcon name="Search" :size="17" /><span>搜索页面</span></button
          ><span class="topbar-rule"></span
          ><button class="factory-button" @click="factoryOpen = true">
            <AppIcon name="Building2" :size="17" /><span>未选择工厂</span
            ><AppIcon name="ChevronDown" :size="14" /></button
          ><button
            class="icon-button desktop-message"
            aria-label="消息入口说明"
            @click="accountOpen = true"
          >
            <AppIcon name="Bell" /></button
          ><button class="account-button" aria-label="账号状态：未登录" @click="accountOpen = true">
            <AppIcon name="CircleUserRound" :size="24" />
          </button>
        </div>
      </header>
      <div class="content-wrap">
        <nav class="breadcrumbs" aria-label="面包屑">
          <RouterLink to="/workbench"
            ><AppIcon name="Home" :size="14" /><span>工作台</span></RouterLink
          ><template v-if="route.meta.moduleId !== 'workbench'"
            ><AppIcon name="ChevronRight" :size="13" /><RouterLink
              v-if="route.meta.detail"
              :to="`/${route.meta.moduleId}`"
              >{{ route.meta.parentTitle }}</RouterLink
            ><AppIcon v-if="route.meta.detail" name="ChevronRight" :size="13" /><span
              aria-current="page"
              >{{ route.meta.title }}</span
            ></template
          >
        </nav>
        <main id="main-content" tabindex="-1"><RouterView :key="route.path" /></main>
        <footer class="workspace-footer">
          <span>加工厂设备运维管理平台</span><span>界面预览 · 无真实业务数据</span>
        </footer>
      </div>
    </div>
    <AppOverlay v-model:open="searchOpen" title="页面导航"
      ><label class="search-field navigation-search"
        ><AppIcon name="Search" :size="18" /><input
          v-model="query"
          placeholder="搜索模块页面"
          aria-label="搜索模块页面"
      /></label>
      <div class="page-search-results">
        <RouterLink v-for="item in pages" :key="item.id" :to="`/${item.id}`"
          ><AppIcon :name="item.icon" :size="18" />{{ item.title
          }}<AppIcon name="ArrowUpRight" :size="16" /></RouterLink
        ><EmptyState
          v-if="!pages.length"
          compact
          title="未找到模块页面"
          description="请尝试其他页面名称。"
        />
      </div>
      <p class="inline-hint">仅搜索页面名称，不搜索工厂或业务记录。</p></AppOverlay
    >
    <AppOverlay v-model:open="factoryOpen" title="选择工厂"
      ><EmptyState
        icon="Building2"
        title="工厂组织尚未接入"
        description="接入组织与工厂服务后，这里将展示经后端授权的工厂范围。"
      /><template #footer
        ><button class="button secondary" @click="factoryOpen = false">关闭</button
        ><button class="button primary" disabled>工厂切换待开发</button></template
      ></AppOverlay
    >
    <AppOverlay v-model:open="accountOpen" title="账号与消息" kind="drawer"
      ><EmptyState
        icon="CircleUserRound"
        title="身份服务尚未接入"
        description="当前没有已登录账号、角色或消息。飞书身份与本地授权将在后续阶段接入。" /><RouterLink
        to="/settings?tab=roles"
        class="button secondary"
        @click="accountOpen = false"
        >查看三角色设计<AppIcon name="ArrowRight" :size="16" /></RouterLink
    ></AppOverlay>
  </div>
</template>
