<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue';
import { identityEnabled } from '../../app/features';
import { useRoute, useRouter } from 'vue-router';
import { assetsApi, AssetApiError } from './api';
import { categories, statuses } from './presentation';
import type { AssetList, AssetStatus, AssetCategory, Factory, DataSource } from './contracts';
import AssetReadState, { type ReadState } from './AssetReadState.vue';
import AssetDataNotice from './AssetDataNotice.vue';
import { config } from './config';
import { useShell } from '../../shared/composables/useShell';
import AppIcon from '../../shared/components/AppIcon.vue';
import PageHeader from '../../shared/components/PageHeader.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import AppOverlay from '../../shared/components/AppOverlay.vue';
const route = useRoute();
const router = useRouter();
const { pathFor } = useShell();
const factories = ref<Factory[]>([]);
const selectedFactory = ref('');
const query = ref('');
const category = ref<AssetCategory | ''>('');
const tab = ref('全部设备');
const state = ref<ReadState>('loading');
const source = ref<DataSource>();
const result = ref<AssetList>();
const offset = ref(0);
const help = ref(false);
let controller: AbortController | undefined;
let delay: ReturnType<typeof setTimeout> | undefined;
let generation = 0;
const status = computed<AssetStatus | undefined>(
  () =>
    (
      ({ 在用设备: 'in_use', '停用 / 封存': 'inactive', 已报废: 'retired' }) as Record<
        string,
        AssetStatus
      >
    )[tab.value],
);
const knownFactory = computed(
  () => !selectedFactory.value || factories.value.some((item) => item.id === selectedFactory.value),
);
async function load() {
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  state.value = 'loading';
  result.value = undefined;
  try {
    const scope = await assetsApi.factories(controller.signal);
    if (current !== generation) return;
    factories.value = scope.items;
    source.value = scope.data_source;
    selectedFactory.value =
      typeof route.query.factory === 'string' ? route.query.factory : (scope.items[0]?.id ?? '');
    if (!selectedFactory.value) {
      state.value = 'forbidden';
      return;
    }
    const page = await assetsApi.search(
      selectedFactory.value,
      {
        q: query.value,
        category: category.value || undefined,
        status: status.value,
        limit: 20,
        offset: offset.value,
      },
      controller.signal,
    );
    if (current !== generation) return;
    result.value = page;
    source.value = page.data_source;
    state.value = page.items.length ? 'loaded' : 'empty';
  } catch (error) {
    if (current !== generation || controller.signal.aborted) return;
    factories.value = [];
    source.value = undefined;
    state.value =
      error instanceof AssetApiError && error.status === 401 && identityEnabled
        ? 'expired'
        : error instanceof AssetApiError && [401, 403].includes(error.status)
          ? 'forbidden'
          : 'error';
  }
}
function selectFactory() {
  offset.value = 0;
  void router.replace({ query: { ...route.query, factory: selectedFactory.value } });
}
function schedule() {
  controller?.abort();
  generation++;
  state.value = 'loading';
  result.value = undefined;
  clearTimeout(delay);
  offset.value = 0;
  delay = setTimeout(() => {
    void load();
  }, 180);
}
watch(
  () => route.query.factory,
  () => {
    offset.value = 0;
    clearTimeout(delay);
    void load();
  },
  { immediate: true },
);
watch([query, category, tab], schedule);
onUnmounted(() => {
  generation++;
  controller?.abort();
  clearTimeout(delay);
});
function paginate(delta: number) {
  offset.value = Math.max(0, offset.value + delta);
  void load();
}
</script>
<template>
  <PageHeader :title="config.title" :description="config.description" :eyebrow="config.english"
    ><template #actions
      ><button class="button secondary" @click="help = true">
        <AppIcon name="BookOpen" :size="17" />接入说明</button
      ><button class="button primary" disabled>
        新增设备<span class="button-tag">待开发</span>
      </button></template
    ></PageHeader
  >
  <AssetDataNotice :source="source" />
  <section class="module-summary" aria-label="模块概况">
    <div>
      <span class="module-summary-icon"><AppIcon name="Boxes" /></span>
      <div>
        <strong>设备基础档案</strong>
        <p>仅查询后端授权工厂范围内的设备，尚不提供业务写入</p>
      </div>
    </div>
    <span class="status-pill neutral">只读 API · M1-01</span>
  </section>
  <section class="panel list-panel" aria-label="设备台账列表">
    <UiTabs v-model="tab" :items="config.tabs" label="设备台账分类">
      <div class="list-toolbar live-assets-toolbar">
        <label class="search-field"
          ><AppIcon name="Search" :size="17" /><input
            v-model="query"
            aria-label="搜索设备"
            placeholder="搜索设备名称或编号"
            maxlength="100"
        /></label>
        <div class="asset-scope-controls">
          <label class="sr-only" for="asset-factory">所属工厂</label
          ><select
            id="asset-factory"
            v-model="selectedFactory"
            aria-label="所属工厂"
            @change="selectFactory"
          >
            <option v-if="!selectedFactory" value="">无可用工厂范围</option>
            <option v-if="!knownFactory" :value="selectedFactory">请求范围未确认</option>
            <option v-for="factory in factories" :key="factory.id" :value="factory.id">
              {{ factory.name }}
            </option></select
          ><select v-model="category" aria-label="设备分类">
            <option value="">全部分类</option>
            <option v-for="(label, key) in categories" :key="key" :value="key">
              {{ label }}
            </option></select
          ><button class="button secondary" @click="load">刷新查询</button>
        </div>
      </div>
      <div v-if="state === 'loaded'" class="table-scroll">
        <table>
          <caption class="sr-only">
            已授权工厂的设备查询结果
          </caption>
          <thead>
            <tr>
              <th>设备编号 / 名称</th>
              <th>分类</th>
              <th>位置</th>
              <th>状态</th>
              <th>厂家 / 型号</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="asset in result?.items" :key="asset.id" class="asset-data-row">
              <td>
                <strong>{{ asset.asset_code }}</strong
                ><span>{{ asset.name }}</span>
              </td>
              <td>{{ categories[asset.category] }}</td>
              <td>{{ asset.location || '—' }}</td>
              <td>{{ statuses[asset.status] }}</td>
              <td>{{ asset.manufacturer || '—' }} / {{ asset.model || '—' }}</td>
              <td>
                <RouterLink
                  :to="{
                    path: pathFor(`assets/${asset.id}`),
                    query: { factory: asset.factory_id },
                  }"
                  class="text-button"
                  >查看详情</RouterLink
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AssetReadState v-else :state="state" @retry="load" />
      <footer class="list-footer">
        <span>{{ result ? `共 ${result.total} 条设备记录` : '未显示业务记录' }}</span>
        <div class="pagination">
          <button
            class="icon-button small"
            :disabled="!result || offset === 0"
            aria-label="上一页"
            @click="paginate(-20)"
          >
            <AppIcon name="ChevronLeft" :size="16" /></button
          ><span>{{ result ? Math.floor(offset / 20) + 1 : '—' }}</span
          ><button
            class="icon-button small"
            :disabled="!result || offset + result.items.length >= result.total"
            aria-label="下一页"
            @click="paginate(20)"
          >
            <AppIcon name="ChevronRight" :size="16" />
          </button>
        </div>
      </footer>
    </UiTabs>
  </section>
  <p class="page-footnote">
    <AppIcon
      name="ShieldCheck"
      :size="14"
    />身份、角色与工厂范围由后端逐次校验，前端选择不能授予权限。
  </p>
  <AppOverlay v-model:open="help" title="设备只读查询接入说明" kind="drawer"
    ><h3>独立数据库，统一授权</h3>
    <p class="form-description">
      {{ identityEnabled ? '本页面只读取后端授权范围中的基础档案。飞书身份与平台会话由后端校验；豆包通道尚未接入。' : '本页面只读取后端授权范围中的基础档案。当前没有飞书或豆包登录入口，已有平台会话由服务端校验；本轮仅在隔离合成测试环境验证。' }}
    </p>
    <ul class="guidance-list">
      <li>新增、编辑、导出、附件与其他运维业务仍待开发。</li>
      <li>切换工厂、搜索及刷新都会重新经过后端授权。</li>
      <li>无权限与查询失败不会显示成“暂无数据”。</li>
    </ul></AppOverlay
  >
</template>
