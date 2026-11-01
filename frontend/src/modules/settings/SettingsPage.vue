<script setup lang="ts">
import { assetsApiEnabled, identityEnabled } from '../../app/features';
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import PeopleManagement from './people/PeopleManagement.vue';
import { account } from '../identity/account';
import { managementRoles } from './roles';
import { useShell } from '../../shared/composables/useShell';
import AppIcon from '../../shared/components/AppIcon.vue';
import PageHeader from '../../shared/components/PageHeader.vue';
import ShellNotice from '../../shared/components/ShellNotice.vue';
import EmptyState from '../../shared/components/EmptyState.vue';
import UiTabs from '../../shared/components/UiTabs.vue';
import AppOverlay from '../../shared/components/AppOverlay.vue';
const route = useRoute();
const router = useRouter();
const { pathFor } = useShell();
const keys = identityEnabled
  ? ['organization', 'people', 'roles', 'integrations', 'general']
  : ['organization', 'roles', 'integrations', 'general'];
const labels = identityEnabled
  ? ['组织与工厂', '人员管理', '角色与范围', '集成设置', '基础设置']
  : ['组织与工厂', '角色与范围', '集成设置', '基础设置'];
const selected = computed({
  get: () => labels[Math.max(0, keys.indexOf(String(route.query.tab ?? 'organization')))]!,
  set: (value) => {
    void router.replace({ query: { tab: keys[labels.indexOf(value)] } });
  },
});
const help = ref('');
const helpOpen = ref(false);
function showHelp(kind: string) {
  help.value = kind;
  helpOpen.value = true;
}
</script>
<template>
  <PageHeader
    title="系统设置"
    description="统一管理平台基础、角色范围与外部集成入口。"
    eyebrow="PLATFORM SETTINGS"
  />
  <ShellNotice />
  <section class="panel settings-panel">
    <UiTabs v-model="selected" :items="labels" label="系统设置分类">
      <template v-if="selected === '组织与工厂'"
        ><header class="settings-section-header">
          <div>
            <h2>组织与工厂</h2>
            <p>工厂是业务资料与访问范围的基本边界</p>
          </div>
          <button class="button primary" disabled>
            新增工厂<span class="button-tag">待开发</span>
          </button>
        </header>
        <div v-if="identityEnabled" class="identity-factory-links">
          <p v-if="!account.user?.factories.length">暂无获授权工厂</p>
          <RouterLink
            v-for="factory in account.user?.factories"
            :key="factory.id"
            :to="{ path: pathFor('assets'), query: { factory: factory.id } }"
            class="button secondary"
            >{{ factory.name }}</RouterLink
          >
        </div>
        <EmptyState
          v-else
          icon="Building2"
          title="组织服务尚未接入"
          description="工厂、车间、区域与位置树将在后续阶段建立，当前没有可管理的组织数据。"
      /></template>
      <PeopleManagement v-else-if="identityEnabled && selected === '人员管理'" />
      <template v-else-if="selected === '角色与范围'"
        ><header class="settings-section-header">
          <div>
            <h2>三种管理角色</h2>
            <p>角色定义操作能力，工厂授权限定数据范围</p>
          </div>
          <span class="status-pill neutral">{{ identityEnabled ? '固定三角色' : '设计预留' }}</span>
        </header>
        <div class="role-grid">
          <article v-for="role in managementRoles" :key="role.code" class="role-card">
            <span class="role-symbol"><AppIcon :name="role.icon" :size="23" /></span>
            <h3>{{ role.name }}</h3>
            <span class="role-scope">{{ role.scope }}</span>
            <p>{{ role.description }}</p>
            <span class="role-code">{{ role.code }}</span>
          </article>
        </div>
        <div class="settings-rule">
          <AppIcon name="ShieldCheck" />
          <div>
            <strong>独立验收，不因角色而例外</strong>
            <p>
              {{
                identityEnabled
                  ? '任何人不得验收本人实际执行的维修工单。人员授权由集团负责人在人员管理中维护，设备访问始终由后端检查当前权限。'
                  : assetsApiEnabled
                    ? '任何人不得验收本人实际执行的维修工单。当前设备查询由后端验证权限，本页不提供授权修改或身份模拟。'
                    : '任何人不得验收本人实际执行的维修工单。当前没有已登录账号、角色分配或权限验证。'
              }}
            </p>
          </div>
        </div>
        <p class="settings-hint">
          员工报修与受限任务执行是特定业务入口，不增加第四种管理角色。
        </p></template
      >
      <template v-else-if="selected === '集成设置'"
        ><header class="settings-section-header">
          <div>
            <h2>外部系统集成</h2>
            <p>保持业务独立，以明确边界连接协作与运行信息</p>
          </div>
        </header>
        <div class="integration-grid">
          <article class="integration-card">
            <div class="integration-card-heading">
              <span class="integration-logo feishu"
                ><AppIcon name="MessageSquareWarning" :size="25" /></span
              ><span class="status-pill neutral">未接入</span>
            </div>
            <h3>飞书企业应用</h3>
            <p>
              {{
                identityEnabled
                  ? '已提供 PC/H5 身份流程，应用凭据仅在服务端配置。通讯录同步与通知尚未接入；飞书身份不会自动授予权限。'
                  : '预留工作台 H5、身份入口与消息通知。飞书身份不自动授予工厂或管理权限。'
              }}
            </p>
            <div class="integration-card-actions">
              <button class="button secondary" @click="showHelp('feishu')">
                查看接入边界<AppIcon name="ArrowRight" :size="16" /></button
              ><button class="text-button" disabled>配置待开发</button>
            </div>
          </article>
          <article class="integration-card">
            <div class="integration-card-heading">
              <span class="integration-logo monitoring"><AppIcon name="Monitor" :size="25" /></span
              ><span class="status-pill neutral">只读预留</span>
            </div>
            <h3>冷库监控</h3>
            <p>仅关联已确认的设备或测点，预留只读摘要与受控跳转。不包含现场设备控制。</p>
            <div class="integration-card-actions">
              <button class="button secondary" @click="showHelp('monitoring')">
                查看接入边界<AppIcon name="ArrowRight" :size="16" /></button
              ><button class="text-button" disabled>配置待开发</button>
            </div>
          </article>
        </div></template
      >
      <template v-else
        ><header class="settings-section-header">
          <div>
            <h2>平台基础信息</h2>
            <p>界面设置与平台信息展示，当前不写入任何配置</p>
          </div>
        </header>
        <div class="settings-form">
          <label class="form-field">平台名称<input value="加工厂设备运维管理平台" disabled /></label
          ><label class="form-field"
            >默认工厂<select disabled>
              <option>工厂组织尚未接入</option>
            </select></label
          ><label class="form-field"
            >业务时区<select disabled>
              <option>待业务确认</option>
            </select></label
          ><button class="button primary" disabled>保存设置 · 待开发</button>
          <div class="settings-design-link">
            <AppIcon name="BookOpen" :size="18" /><RouterLink
              :to="pathFor('design-system')"
              class="text-button"
              >查看界面组件规范<AppIcon name="ArrowRight" :size="16"
            /></RouterLink>
          </div></div
      ></template>
    </UiTabs>
  </section>
  <AppOverlay
    v-model:open="helpOpen"
    :title="help === 'feishu' ? '飞书接入边界' : '监控只读接入边界'"
    kind="drawer"
    ><div class="connection-mark">
      <AppIcon :name="help === 'feishu' ? 'Fingerprint' : 'Monitor'" :size="28" />
    </div>
    <h3>{{ help === 'feishu' ? '身份校验与本地授权分离' : '只补充运行事实，不下发控制命令' }}</h3>
    <p class="form-description">
      {{
        help === 'feishu'
          ? identityEnabled
            ? 'PC/H5 使用官方 OAuth 重定向，后端交换授权码并校验租户及用户，平台独立保存授权。未配置时认证关闭，通讯录同步和通知尚未接入。'
            : '当前未加载飞书 SDK，不请求登录凭证、不创建应用、不发送通知，也不读取员工资料。后续由后端校验企业身份并绑定本地用户，按工厂校验授权。'
          : '当前不访问监控服务。后续仅使用经确认的只读 API，保留设备、机位、位置、测点的独立身份与映射有效期；告警恢复不自动关闭工单。'
      }}
    </p>
    <ul class="guidance-list">
      <li>实际接口与企业配置均未核实。</li>
      <li>本页面不接受或保存任何密钥。</li>
      <li>未接入功能不会展示成功状态。</li>
    </ul></AppOverlay
  >
</template>
