<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from '../../shared/components/AppIcon.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
const tab = ref('全部任务');
</script>
<template>
  <header class="mobile-page-heading">
    <span class="eyebrow">MY TASKS</span>
    <h1>我的任务</h1>
    <p>被指派的现场工作，在这里有序进行。</p>
  </header>
  <section class="panel">
    <UiTabs v-model="tab" :items="['全部任务', '巡检', '维修', '保养']" label="移动任务分类"
      ><EmptyState
        icon="ClipboardList"
        title="任务服务尚未接入"
        description="当前没有已登录人员，也未加载任何任务记录。"
    /></UiTabs>
  </section>
  <section class="mobile-preview-links">
    <h2>查看页面结构</h2>
    <p>以下入口仅展示详情框架，非真实任务。</p>
    <RouterLink to="/m/inspections/preview"
      ><AppIcon name="ClipboardCheck" :size="20" /><span>巡检任务结构</span
      ><AppIcon name="ChevronRight" :size="16" /></RouterLink
    ><RouterLink to="/m/work-orders/preview"
      ><AppIcon name="Wrench" :size="20" /><span>维修工单结构</span
      ><AppIcon name="ChevronRight" :size="16"
    /></RouterLink>
  </section>
</template>
