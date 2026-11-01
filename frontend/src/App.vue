<script setup lang="ts">
import { navigating } from './app/router';
</script>
<template>
  <div v-if="navigating" class="route-progress" role="status" aria-label="正在打开页面"></div>
  <RouterView />
</template>
