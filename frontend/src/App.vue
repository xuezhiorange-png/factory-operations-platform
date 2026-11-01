<script setup lang="ts">
import { failedRoute, navigating } from './app/router';
import RouteLoadFailure from './app/RouteLoadFailure.vue';
</script>
<template>
  <div v-if="navigating" class="route-progress" role="status" aria-label="正在打开页面"></div>
  <RouteLoadFailure v-if="failedRoute" />
  <RouterView v-else />
</template>
