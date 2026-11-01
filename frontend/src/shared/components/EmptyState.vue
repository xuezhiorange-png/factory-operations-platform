<script setup lang="ts">
import AppIcon from './AppIcon.vue';
import type { IconName } from '../icons';
withDefaults(
  defineProps<{ title?: string; description?: string; icon?: IconName; compact?: boolean }>(),
  {
    title: '业务数据尚未接入',
    description: '接入业务服务后，相关记录将在这里呈现。',
    icon: 'Inbox',
    compact: false,
  },
);
</script>
<template>
  <div class="empty-state" :class="{ compact }">
    <div class="empty-illustration" aria-hidden="true">
      <span></span><AppIcon :name="icon" :size="28" /><span></span>
    </div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <div v-if="$slots.default" class="empty-actions"><slot /></div>
  </div>
</template>
