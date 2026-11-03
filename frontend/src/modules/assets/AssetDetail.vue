<script setup lang="ts">
import { useRoute } from 'vue-router';
import { assetsApiEnabled } from '../../app/features';
import AssetLiveDetail from './AssetLiveDetail.vue';
import DetailPage from '../../shared/components/DetailPage.vue';
import { detailConfig as config } from './config';
const route = useRoute();
</script>
<template>
  <AssetLiveDetail
    v-if="assetsApiEnabled && route.params.id !== 'preview'"
    :config="config"
  /><DetailPage v-else :config="config" />
</template>
