<script setup lang="ts">
import { identityEnabled } from '../../app/features';
import { accountLabel } from '../identity/account';
import { navigation } from '../../app/navigation';
import AppIcon from '../../shared/components/AppIcon.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
import ShellNotice from '../../shared/components/ShellNotice.vue';
</script>
<template>
  <section class="mobile-greeting">
    <span class="eyebrow">MOBILE WORKSPACE</span>
    <h1>现场工作，有序连接</h1>
    <p>设备、任务与消息，随时找到清晰入口。</p>
    <span class="mobile-preview-label"
      ><span class="status-dot"></span
      >{{ identityEnabled ? accountLabel : 'H5 界面预览 · 未登录' }}</span
    >
  </section>
  <ShellNotice />
  <section class="mobile-metrics" aria-label="任务概况">
    <div v-for="title in ['今日待办', '已逾期', '待验收']" :key="title">
      <span>{{ title }}</span
      ><strong>—</strong><small>待接入</small>
    </div>
  </section>
  <section class="panel mobile-module-panel">
    <header class="section-heading">
      <h2>工作入口</h2>
      <span class="subtle-label">全部模块</span>
    </header>
    <div class="mobile-module-grid">
      <RouterLink v-for="item in navigation.slice(1)" :key="item.id" :to="`/m/${item.id}`"
        ><span><AppIcon :name="item.icon" :size="23" /></span
        ><strong>{{ item.title }}</strong></RouterLink
      >
    </div>
  </section>
  <section class="panel mobile-today">
    <header class="section-heading">
      <h2>我的今日任务</h2>
      <RouterLink to="/m/tasks" class="text-button"
        >查看全部<AppIcon name="ChevronRight" :size="15"
      /></RouterLink>
    </header>
    <EmptyState
      compact
      icon="ClipboardList"
      title="任务服务尚未接入"
      description="巡检、维修与保养任务将在这里集中呈现。"
    />
  </section>
  <p class="mobile-safe-note">
    <AppIcon name="ShieldCheck" :size="15" />仅预览界面，不执行现场设备操作
  </p>
</template>
