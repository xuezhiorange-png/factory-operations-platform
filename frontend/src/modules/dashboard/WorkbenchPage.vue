<script setup lang="ts">
import { ref } from 'vue';
import { navigation } from '../../app/navigation';
import AppIcon from '../../shared/components/AppIcon.vue';
import PageHeader from '../../shared/components/PageHeader.vue';
import ShellNotice from '../../shared/components/ShellNotice.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import AppOverlay from '../../shared/components/AppOverlay.vue';
const taskTab = ref('全部待办');
const guideOpen = ref(false);
const metrics = [
  { title: '设备资产', icon: 'Boxes' as const, note: '待接入设备台账', accent: 'sage' },
  { title: '待执行任务', icon: 'ClipboardCheck' as const, note: '待接入任务服务', accent: 'blue' },
  { title: '待验收工单', icon: 'Wrench' as const, note: '待接入维修工单', accent: 'sand' },
  { title: '设备可用率', icon: 'BarChart3' as const, note: '暂无可计算数据', accent: 'lilac' },
];
</script>
<template>
  <PageHeader
    title="工作台"
    description="设备运维，从清晰有序开始。"
    eyebrow="YOUR OPERATIONS, CONNECTED"
  >
    <template #actions
      ><button class="button secondary" @click="guideOpen = true">
        <AppIcon name="CircleHelp" :size="17" />平台使用说明
      </button></template
    >
  </PageHeader>
  <ShellNotice />
  <section class="metrics-grid" aria-label="运维概况">
    <article v-for="item in metrics" :key="item.title" class="panel metric-card">
      <div class="metric-label">
        <span>{{ item.title }}</span
        ><span class="metric-icon" :class="item.accent"
          ><AppIcon :name="item.icon" :size="19"
        /></span>
      </div>
      <strong class="metric-value">—</strong>
      <p><span class="status-dot"></span>{{ item.note }}</p>
    </article>
  </section>
  <div class="dashboard-columns">
    <section class="panel task-panel">
      <header class="section-heading padded">
        <div>
          <h2>我的待办</h2>
          <p>聚焦需要跟进的每一件事</p>
        </div>
        <span class="status-pill neutral">待接入</span>
      </header>
      <UiTabs
        v-model="taskTab"
        :items="['全部待办', '巡检任务', '维修工单', '保养任务']"
        label="待办类别"
        ><EmptyState
          icon="ClipboardList"
          title="任务服务尚未接入"
          description="后续将在这里集中查看被指派的巡检、维修与保养任务。"
          ><RouterLink to="/inspections" class="button secondary"
            >前往巡检管理<AppIcon name="ArrowRight" :size="16" /></RouterLink></EmptyState
      ></UiTabs>
    </section>
    <aside class="dashboard-aside">
      <section class="panel quick-panel">
        <header class="section-heading">
          <h2>快捷入口</h2>
          <AppIcon name="ArrowUpRight" :size="18" />
        </header>
        <div class="quick-grid">
          <RouterLink v-for="item in navigation.slice(1, 5)" :key="item.id" :to="`/${item.id}`"
            ><span><AppIcon :name="item.icon" :size="22" /></span
            ><strong>{{ item.title }}</strong></RouterLink
          >
        </div>
      </section>
      <section class="panel integration-panel">
        <header class="section-heading">
          <h2>连接与集成</h2>
          <RouterLink to="/settings?tab=integrations" class="text-button"
            >设置<AppIcon name="ChevronRight" :size="14"
          /></RouterLink>
        </header>
        <div class="connection-row">
          <span class="connection-icon"><AppIcon name="Building2" :size="18" /></span
          ><span>组织与工厂</span><span class="connection-state">未接入</span>
        </div>
        <div class="connection-row">
          <span class="connection-icon"><AppIcon name="MessageSquareWarning" :size="18" /></span
          ><span>飞书企业应用</span><span class="connection-state">未接入</span>
        </div>
        <div class="connection-row">
          <span class="connection-icon"><AppIcon name="Monitor" :size="18" /></span
          ><span>冷库监控</span><span class="connection-state">只读预留</span>
        </div>
      </section>
    </aside>
  </div>
  <section class="panel process-panel">
    <header class="section-heading">
      <div>
        <h2>让设备管理形成闭环</h2>
        <p>一套入口，连接资产、现场任务与维修履历</p>
      </div>
      <span class="subtle-label">业务流程规划</span>
    </header>
    <div class="process-steps">
      <RouterLink v-for="(item, index) in navigation.slice(1, 5)" :key="item.id" :to="`/${item.id}`"
        ><span class="step-number">0{{ index + 1 }}</span>
        <div>
          <strong>{{ item.title }}</strong
          ><small>{{
            ['建立设备身份', '按标准执行检查', '记录与分诊异常', '维修与独立验收'][index]
          }}</small>
        </div>
        <AppIcon name="ArrowRight" :size="17"
      /></RouterLink>
    </div>
  </section>
  <AppOverlay v-model:open="guideOpen" title="关于当前平台" kind="drawer"
    ><div class="connection-mark"><AppIcon name="Boxes" :size="28" /></div>
    <h3>先让协作有清晰的入口</h3>
    <p class="form-description">
      当前版本完成管理端与移动端的页面框架，方便评审导航、信息层级和使用体验。
    </p>
    <ul class="guidance-list">
      <li>所有指标显示“—”，不代表设备或任务数量为零。</li>
      <li>详情为结构预览，不对应真实业务记录。</li>
      <li>未实现的新增、保存、导出等操作已禁用。</li>
      <li>没有登录会话、实际权限、飞书或监控连接。</li>
    </ul>
    <RouterLink to="/m/home" class="button secondary" @click="guideOpen = false"
      >查看移动工作台<AppIcon name="Smartphone" :size="17" /></RouterLink
  ></AppOverlay>
</template>
