<script setup lang="ts">
import { icons, type IconName } from '../icons';
withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 20 });
</script>
<template>
  <component :is="icons[name]" :size="size" :stroke-width="1.7" aria-hidden="true" />
</template>
