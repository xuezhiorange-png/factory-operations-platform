<script setup lang="ts">
import { useRoute } from 'vue-router';
import EmptyState from '../../shared/components/EmptyState.vue';
const route = useRoute();
</script>
<template><section class="operations-pending"><EmptyState :title="`${route.meta.title} · 待开发`" description="业务尚未接入，当前没有可操作的记录。" icon="Wrench" /></section></template>
