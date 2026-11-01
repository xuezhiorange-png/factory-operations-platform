<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ModuleConfig } from '../types';
import { useShell } from '../composables/useShell';
import AppIcon from './AppIcon.vue';
import PageHeader from './PageHeader.vue';
import EmptyState from './EmptyState.vue';
import ShellNotice from './ShellNotice.vue';
import UiTabs from './UiTabs.vue';
import AppOverlay from './AppOverlay.vue';
const props = defineProps<{ config: ModuleConfig }>();
const { pathFor } = useShell();
const active = ref(props.config.tabs[0]!);
const search = ref('');
const filter = ref('');
const filterOpen = ref(false);
const helpOpen = ref(false);
const hasFilters = computed(() => Boolean(search.value.trim() || filter.value));
function reset() {
  search.value = '';
  filter.value = '';
}
</script>
<template>
  <PageHeader :title="config.title" :description="config.description" :eyebrow="config.english">
    <template #actions
      ><button class="button secondary" @click="helpOpen = true">
        <AppIcon name="BookOpen" :size="17" />接入说明</button
      ><button class="button primary" disabled :title="`${config.action}待开发`">
        <AppIcon name="Plus" :size="18" />{{ config.action }}<span class="button-tag">待开发</span>
      </button></template
    >
  </PageHeader>
  <ShellNotice />
  <section class="module-summary" aria-label="模块概况">
    <div>
      <span class="module-summary-icon"><AppIcon :name="config.icon" /></span>
      <div>
        <strong>{{ config.noun }}管理</strong>
        <p>从统一档案到完整履历，有序连接每个环节</p>
      </div>
    </div>
    <span class="status-pill neutral"
      ><span class="status-dot"></span>待接入 · {{ config.stage }}</span
    >
  </section>
  <section class="panel list-panel" :aria-label="`${config.title}列表`">
    <UiTabs v-model="active" :items="config.tabs" :label="`${config.title}分类`">
      <div class="list-toolbar">
        <label class="search-field"
          ><AppIcon name="Search" :size="17" /><input
            v-model="search"
            :aria-label="`搜索${config.noun}`"
            :placeholder="`搜索${config.noun}名称或编号`" /><button
            v-if="search"
            class="icon-button small"
            :aria-label="`清除${config.noun}搜索`"
            @click="search = ''"
          >
            <AppIcon name="X" :size="15" /></button
        ></label>
        <div class="toolbar-actions">
          <button
            class="button secondary"
            :class="{ 'has-filter': filter }"
            @click="filterOpen = true"
          >
            <AppIcon name="ListFilter" :size="16" />筛选<span
              v-if="filter"
              class="filter-dot"
            ></span></button
          ><button class="button secondary export-button" disabled title="导出待开发">
            <AppIcon name="ArrowDownToLine" :size="16" />导出
          </button>
        </div>
      </div>
      <div v-if="hasFilters" class="filter-feedback" role="status">
        界面筛选条件已更新，业务查询尚未接入。<button class="text-button" @click="reset">
          重置筛选
        </button>
      </div>
      <div class="table-scroll">
        <table>
          <caption class="sr-only">
            {{
              config.title
            }}，业务服务未接入，当前无记录
          </caption>
          <thead>
            <tr>
              <th v-for="column in config.columns" :key="column" scope="col">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td :colspan="config.columns.length">
                <EmptyState
                  :icon="config.icon"
                  :title="hasFilters ? '当前没有可查询的业务数据' : `${config.noun}数据尚未接入`"
                  :description="
                    hasFilters
                      ? '当前筛选仅展示交互，不执行真实查询。'
                      : `接入${config.title}服务后，可在此查看、筛选和管理记录。`
                  "
                >
                  <RouterLink
                    v-if="config.detailPath"
                    :to="pathFor(config.detailPath)"
                    class="button secondary"
                    >预览详情结构<AppIcon name="ArrowRight" :size="16"
                  /></RouterLink>
                  <button v-else class="button secondary" @click="helpOpen = true">
                    查看接入说明<AppIcon name="ArrowRight" :size="16" />
                  </button>
                </EmptyState>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer class="list-footer">
        <span>无业务记录 <span class="muted-separator">/</span> {{ active }}</span>
        <div class="pagination">
          <span>— / —</span
          ><button class="icon-button small" disabled aria-label="上一页">
            <AppIcon name="ChevronLeft" :size="16" /></button
          ><button class="icon-button small" disabled aria-label="下一页">
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
    />数据访问与操作权限将在后端接入后校验，当前页面不提供业务授权。
  </p>
  <AppOverlay v-model:open="filterOpen" title="筛选条件" kind="drawer">
    <p class="form-description">仅预览筛选交互，当前不会请求或保存业务数据。</p>
    <label class="form-field"
      >所属工厂<select disabled>
        <option>工厂组织尚未接入</option>
      </select></label
    >
    <label class="form-field"
      >{{ config.filterLabel
      }}<select v-model="filter">
        <option value="">全部</option>
        <option v-for="option in config.filterOptions" :key="option">{{ option }}</option>
      </select></label
    >
    <p class="inline-hint"><AppIcon name="Info" :size="16" />条件仅保留在当前页面，刷新后重置。</p>
    <template #footer
      ><button class="button secondary" @click="reset">重置</button
      ><button class="button primary" @click="filterOpen = false">查看筛选条件</button></template
    >
  </AppOverlay>
  <AppOverlay v-model:open="helpOpen" :title="`${config.title}接入说明`" kind="drawer">
    <div class="connection-mark"><AppIcon :name="config.icon" :size="28" /></div>
    <h3>页面已就绪，业务待接入</h3>
    <p class="form-description">{{ config.boundary }}</p>
    <ul class="guidance-list">
      <li>当前不查询、不创建、不修改任何业务记录。</li>
      <li>列表、详情、筛选和导出需逐项接入后端。</li>
      <li>所有资源访问需要服务端身份与工厂范围校验。</li>
    </ul>
    <span class="status-pill neutral">计划阶段 {{ config.stage }}</span>
  </AppOverlay>
</template>
