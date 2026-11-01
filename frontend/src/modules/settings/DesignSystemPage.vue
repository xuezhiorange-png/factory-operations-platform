<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from '../../shared/components/AppIcon.vue';
import PageHeader from '../../shared/components/PageHeader.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
import LoadingState from '../../shared/components/LoadingState.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import AppOverlay from '../../shared/components/AppOverlay.vue';
const state = ref('空状态');
const dialogOpen = ref(false);
const drawerOpen = ref(false);
</script>
<template>
  <PageHeader
    title="界面组件规范"
    description="供界面评审使用的组件展示，不对应业务操作。"
    eyebrow="DESIGN FOUNDATIONS"
  />
  <section class="panel design-panel">
    <h2>颜色与层级</h2>
    <div class="color-grid">
      <div
        v-for="color in [
          { name: '运维青', value: '#326B5B' },
          { name: '深墨', value: '#172F36' },
          { name: '浅灰', value: '#F4F6F7' },
          { name: '边界灰', value: '#E2E8E7' },
        ]"
        :key="color.name"
      >
        <span :style="{ background: color.value }"></span><strong>{{ color.name }}</strong
        ><small>{{ color.value }}</small>
      </div>
    </div>
  </section>
  <section class="panel design-panel">
    <h2>按钮与反馈</h2>
    <div class="component-row">
      <button class="button primary" @click="dialogOpen = true">打开弹窗</button
      ><button class="button secondary" @click="drawerOpen = true">
        打开抽屉<AppIcon name="ArrowRight" :size="16" /></button
      ><button class="button primary" disabled>保存 · 待开发</button
      ><span class="status-pill neutral">未接入</span>
    </div>
    <label class="form-field design-input"
      >只读表单预留<input value="业务字段尚未接入" disabled
    /></label>
  </section>
  <section class="panel">
    <UiTabs v-model="state" :items="['空状态', '加载状态']" label="组件状态展示"
      ><EmptyState v-if="state === '空状态'" title="业务数据尚未接入" /><LoadingState v-else
    /></UiTabs>
  </section>
  <AppOverlay v-model:open="dialogOpen" title="弹窗组件展示"
    ><p class="form-description">
      此弹窗展示键盘焦点、关闭与遮罩交互。没有业务表单，也不会执行保存。
    </p>
    <template #footer
      ><button class="button secondary" @click="dialogOpen = false">关闭展示</button
      ><button class="button primary" disabled>保存 · 待开发</button></template
    ></AppOverlay
  >
  <AppOverlay v-model:open="drawerOpen" title="抽屉组件展示" kind="drawer"
    ><EmptyState
      compact
      icon="Settings2"
      title="抽屉内容区域"
      description="用于筛选、说明或详情补充，当前不读写业务数据。"
  /></AppOverlay>
</template>
