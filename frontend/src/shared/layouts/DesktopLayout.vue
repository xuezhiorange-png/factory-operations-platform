<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { assetsApiEnabled } from '../../app/features';
import { navigation } from '../../app/navigation';
import AppIcon from '../components/AppIcon.vue';
import AppOverlay from '../components/AppOverlay.vue';
import EmptyState from '../components/EmptyState.vue';
import SidebarNavigation from '../components/SidebarNavigation.vue';
const route = useRoute();
const sidebarOpen = ref(false);
const narrowScreen = window.matchMedia('(max-width: 760px)');
const isNarrow = ref(narrowScreen.matches);
function updateViewport(event: MediaQueryListEvent) {
  sidebarOpen.value = false;
  isNarrow.value = event.matches;
}
onMounted(() => narrowScreen.addEventListener('change', updateViewport));
onUnmounted(() => narrowScreen.removeEventListener('change', updateViewport));
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

    <aside v-if="!isNarrow" id="main-sidebar" class="sidebar">
      <SidebarNavigation />
    </aside>
    <AppOverlay
      v-if="isNarrow"
      id="main-sidebar"
      v-model:open="sidebarOpen"
      title="导航菜单"
      kind="drawer"
      class="navigation-drawer"
      ><SidebarNavigation
    /></AppOverlay>
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
          ><button
            class="account-button"
            :aria-label="assetsApiEnabled ? '身份接入说明' : '账号状态：未登录'"
            @click="accountOpen = true"
          >
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
    <AppOverlay v-model:open="factoryOpen" :title="assetsApiEnabled ? '工厂查询范围' : '选择工厂'"
      ><EmptyState
        icon="Building2"
        :title="assetsApiEnabled ? '设备页按服务端授权选择工厂' : '工厂组织尚未接入'"
        description="接入组织与工厂服务后，这里将展示经后端授权的工厂范围。"
      /><template #footer
        ><button class="button secondary" @click="factoryOpen = false">关闭</button
        ><button class="button primary" disabled>工厂切换待开发</button></template
      ></AppOverlay
    >
    <AppOverlay v-model:open="accountOpen" title="账号与消息" kind="drawer"
      ><EmptyState
        icon="CircleUserRound"
        :title="assetsApiEnabled ? '飞书与豆包身份通道待接入' : '身份服务尚未接入'"
        :description="
          assetsApiEnabled
            ? '设备查询仅接受后端验证的平台会话，本界面不提供登录、角色切换或消息服务。'
            : '当前没有已登录账号、角色或消息。飞书身份与本地授权将在后续阶段接入。'
        " /><RouterLink
        to="/settings?tab=roles"
        class="button secondary"
        @click="accountOpen = false"
        >查看三角色设计<AppIcon name="ArrowRight" :size="16" /></RouterLink
    ></AppOverlay>
  </div>
</template>
