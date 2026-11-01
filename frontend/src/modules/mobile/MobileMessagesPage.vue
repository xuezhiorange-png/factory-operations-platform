<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from '../../shared/components/AppIcon.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
const tab = ref('全部消息');
</script>
<template>
  <header class="mobile-page-heading">
    <span class="eyebrow">NOTIFICATIONS</span>
    <h1>消息中心</h1>
    <p>任务提醒与协作通知，统一收纳。</p>
  </header>
  <section class="panel">
    <UiTabs v-model="tab" :items="['全部消息', '任务提醒', '系统通知']" label="消息分类"
      ><EmptyState
        icon="Bell"
        title="消息服务尚未接入"
        description="当前没有真实通知，未连接飞书机器人或企业消息。"
    /></UiTabs>
    <footer class="message-footer">
      <button class="text-button" disabled>
        <AppIcon name="CheckCheck" :size="16" />全部已读 · 待开发
      </button>
    </footer>
  </section>
</template>
