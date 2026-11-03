<script setup lang="ts">
import { identityEnabled } from "../../app/features";
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { assetsApi, AssetApiError } from "./api";
import { categories, statuses } from "./presentation";
import type { AssetDetail } from "./contracts";
import type { DetailConfig } from "../../shared/types";
import AssetReadState, { type ReadState } from "./AssetReadState.vue";
import AssetDataNotice from "./AssetDataNotice.vue";
import DetailPage from "../../shared/components/DetailPage.vue";
import PageHeader from "../../shared/components/PageHeader.vue";
import { useShell } from "../../shared/composables/useShell";
const props = defineProps<{ config: DetailConfig }>();
const route = useRoute();
const { pathFor } = useShell();
const state = ref<ReadState>("loading");
const result = ref<AssetDetail>();
const factoryName = ref("");
let controller: AbortController | undefined;
let generation = 0;
async function load() {
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  state.value = "loading";
  result.value = undefined;
  try {
    const factory =
      typeof route.query.factory === "string" ? route.query.factory : "";
    if (!factory) {
      state.value = "forbidden";
      return;
    }
    const [data, scope] = await Promise.all([
      assetsApi.detail(factory, String(route.params.id), controller.signal),
      assetsApi.factories(controller.signal),
    ]);
    if (current !== generation) return;
    factoryName.value =
      scope.items.find((item) => item.id === factory)?.name ?? "已授权工厂";
    result.value = data;
    state.value = "loaded";
  } catch (error) {
    if (current !== generation || controller.signal.aborted) return;
    state.value =
      error instanceof AssetApiError && error.status === 401 && identityEnabled ? "expired" : error instanceof AssetApiError && [401, 403].includes(error.status)
        ? "forbidden"
        : error instanceof AssetApiError && error.status === 404
          ? "not-found"
          : "error";
  }
}
watch(
  () => route.fullPath,
  () => {
    void load();
  },
  { immediate: true },
);
onUnmounted(() => {
  generation++;
  controller?.abort();
});
const record = computed(() => {
  if (!result.value) return undefined;
  const asset = result.value.asset;
  return {
    label: asset.name,
    values: {
      设备编号: asset.asset_code,
      设备名称: asset.name,
      设备分类: categories[asset.category],
      归属工厂: factoryName.value,
      "厂家 / 型号": `${asset.manufacturer || "—"} / ${asset.model || "—"}`,
      出厂编号: asset.serial_number || "—",
      物理位置: asset.location || "—",
      生命周期: statuses[asset.status],
    },
  };
});
</script>
<template>
  <DetailPage
    v-if="result && record"
    :config="props.config"
    :record="record"
    :back-to="{
      path: pathFor('assets'),
      query: { factory: route.query.factory },
    }"
    ><template #notice
      ><AssetDataNotice :source="result.data_source" /><slot name="monitor-link" :asset="result.asset" /></template
  ></DetailPage>
  <template v-else
    ><RouterLink
      class="back-link"
      :to="{ path: pathFor('assets'), query: { factory: route.query.factory } }"
      >返回设备台账</RouterLink
    ><PageHeader
      :title="config.title"
      :description="config.description"
      eyebrow="ASSET READ" /><AssetDataNotice />
    <section class="panel">
      <AssetReadState :state="state" @retry="load" /></section
  ></template>
</template>
