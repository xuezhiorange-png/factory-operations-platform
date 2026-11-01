<script setup lang="ts">
import { ref } from 'vue';
import type { DetailConfig } from '../types';
import { useShell } from '../composables/useShell';
import AppIcon from './AppIcon.vue';
import PageHeader from './PageHeader.vue';
import EmptyState from './EmptyState.vue';
import UiTabs from './UiTabs.vue';
import ShellNotice from './ShellNotice.vue';
const props = defineProps<{ config: DetailConfig }>();
const { pathFor } = useShell();
const tab = ref(props.config.tabs[0]!);
</script>
<template>
  <RouterLink class="back-link" :to="pathFor(config.moduleId)"
    ><AppIcon name="ArrowLeft" :size="16" />返回{{ config.parent }}</RouterLink
  >
  <PageHeader :title="config.title" :description="config.description" eyebrow="DETAIL STRUCTURE">
    <template #actions
      ><button class="button primary" disabled :title="`${config.action}待开发`">
        {{ config.action }}<span class="button-tag">待开发</span>
      </button></template
    >
  </PageHeader>
  <ShellNotice detail />
  <div class="detail-heading panel">
    <div class="detail-symbol"><AppIcon :name="config.icon" :size="28" /></div>
    <div>
      <h2>{{ config.title }}结构预览</h2>
      <p>尚未加载实体资料</p>
    </div>
    <span class="status-pill neutral">业务未接入</span>
  </div>
  <div class="detail-grid">
    <section class="panel detail-main">
      <UiTabs v-model="tab" :items="config.tabs" :label="`${config.title}内容`">
        <dl v-if="tab === config.tabs[0]" class="detail-fields">
          <div v-for="field in config.fields" :key="field">
            <dt>{{ field }}</dt>
            <dd>—</dd>
          </div>
        </dl>
        <EmptyState
          v-else
          :title="`${tab}尚未接入`"
          description="接入业务服务后，将展示该记录关联的信息与完整履历。"
          :icon="config.icon"
        />
        <p class="detail-note">仅展示字段与信息层级，不代表存在真实{{ config.title }}记录。</p>
      </UiTabs>
    </section>
    <aside class="detail-aside">
      <section class="panel side-panel">
        <div class="section-heading">
          <h2>{{ config.sideTitle }}</h2>
          <AppIcon name="Clock3" :size="18" />
        </div>
        <EmptyState
          compact
          :icon="config.moduleId === 'assets' ? 'QrCode' : 'ClipboardList'"
          title="待接入"
          :description="config.sideDescription"
        />
      </section>
      <section class="quiet-card">
        <AppIcon name="ShieldCheck" />
        <h3>每一步，都有据可查</h3>
        <p>业务接入后，操作时间、人员和变更原因将在履历中保留。</p>
      </section>
    </aside>
  </div>
</template>
