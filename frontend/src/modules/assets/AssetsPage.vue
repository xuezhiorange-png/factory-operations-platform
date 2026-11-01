<script setup lang="ts">
import { assetsApiEnabled } from '../../app/features';
import AssetsLivePage from './AssetsLivePage.vue';
import ModulePage from '../../shared/components/ModulePage.vue';
import { config } from './config';
</script>
<template>
  <AssetsLivePage v-if="assetsApiEnabled" /><ModulePage v-else :config="config" />
</template>
