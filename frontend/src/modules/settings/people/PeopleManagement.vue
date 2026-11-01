<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  personnelApi,
  PersonnelError,
  type Person,
  type PageResult,
  type ChangeRecord,
  type MutationResult,
} from './api';
import { account, roleNames, loginTarget, refreshAccount, type Role } from '../../identity/account';
import { assetsApi, AssetApiError } from '../../assets/api';
import type { Factory } from '../../assets/contracts';
import AppOverlay from '../../../shared/components/AppOverlay.vue';
import EmptyState from '../../../shared/components/EmptyState.vue';
const route = useRoute();
const router = useRouter();
const people = ref<PageResult<Person>>();
const factories = ref<Factory[]>([]);
const state = ref<'loading' | 'loaded' | 'forbidden' | 'expired' | 'error'>('loading');
const offset = ref(0);
const selected = ref<Person>();
const open = ref(false);
const mode = ref<'edit' | 'history'>('edit');
const records = ref<PageResult<ChangeRecord>>();
const historyOffset = ref(0);
const historyState = ref<'loading' | 'loaded' | 'error'>('loading');
const draftRole = ref<Role | ''>('');
const draftActive = ref(true);
const scope = ref<string[]>([]);
const reason = ref('');
const busy = ref(false);
const message = ref('');
const operationError = ref('');
const confirmation = ref<'revoke-sessions' | 'unbind-feishu'>();
let controller: AbortController | undefined;
let historyController: AbortController | undefined;
let generation = 0;
let historyGeneration = 0;
let disposed = false;
const roleLabel = (role: Role | null) => (role ? roleNames[role] : '待授权');
const bindingLabel = (value: Person['feishu_binding']) =>
  ({ bound: '已绑定', unbound: '已解绑', none: '未绑定' })[value];
const factoryNames = (ids: string[]) =>
  ids.map((id) => factories.value.find((f) => f.id === id)?.name ?? '历史工厂').join('、') || '无';
const changed = computed(
  () =>
    selected.value &&
    (draftRole.value !== (selected.value.role ?? '') ||
      draftActive.value !== selected.value.active ||
      [...scope.value].sort().join(',') !==
        selected.value.factories
          .map((f) => f.id)
          .sort()
          .join(',')),
);
const hasReason = computed(() => reason.value.trim().length >= 2);
watch(draftRole, (value) => {
  if (
    !['engineer', 'factory_equipment_admin'].includes(value) ||
    (value === 'factory_equipment_admin' && scope.value.length > 1)
  )
    scope.value = [];
});
async function load() {
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  people.value = undefined;
  state.value = 'loading';
  if (account.user?.role !== 'group_lead') {
    state.value = 'forbidden';
    return;
  }
  try {
    const [result, catalog] = await Promise.all([
      personnelApi.list(offset.value, controller.signal),
      assetsApi.factories(controller.signal),
    ]);
    if (current !== generation || disposed) return;
    people.value = result;
    factories.value = catalog.items;
    state.value = 'loaded';
  } catch (error) {
    if (current !== generation || disposed || controller.signal.aborted) return;
    state.value =
      (error instanceof PersonnelError || error instanceof AssetApiError) && error.status === 401
        ? 'expired'
        : (error instanceof PersonnelError || error instanceof AssetApiError) &&
            error.status === 403
          ? 'forbidden'
          : 'error';
  }
}
function edit(person: Person) {
  selected.value = person;
  draftRole.value = person.role ?? '';
  draftActive.value = person.active;
  scope.value = person.factories.map((f) => f.id);
  reason.value = '';
  operationError.value = '';
  confirmation.value = undefined;
  mode.value = 'edit';
  open.value = true;
}
async function showHistory(person: Person) {
  selected.value = person;
  mode.value = 'history';
  open.value = true;
  historyOffset.value = 0;
  await history();
}
async function history() {
  if (!selected.value) return;
  const id = selected.value.id;
  const current = ++historyGeneration;
  historyController?.abort();
  historyController = new AbortController();
  records.value = undefined;
  historyState.value = 'loading';
  try {
    const result = await personnelApi.history(id, historyOffset.value, historyController.signal);
    if (current !== historyGeneration || selected.value?.id !== id || disposed) return;
    records.value = result;
    historyState.value = 'loaded';
  } catch {
    if (current === historyGeneration && !disposed && !historyController.signal.aborted)
      historyState.value = 'error';
  }
}
async function apply(result: MutationResult) {
  if (disposed) return;
  selected.value = result.user;
  open.value = false;
  message.value = '变更已由服务端确认，旧会话已撤销。';
  if (result.reauthentication_required) {
    await refreshAccount();
    await router.replace({
      path: loginTarget(route.path),
      query: { return_to: route.fullPath, status: 'expired' },
    });
    return;
  }
  await load();
}
async function submit(operation?: 'revoke-sessions' | 'unbind-feishu') {
  if (!selected.value || busy.value || !hasReason.value) return;
  busy.value = true;
  operationError.value = '';
  message.value = '';
  const id = selected.value.id;
  const body = { expected_version: selected.value.version, reason: reason.value.trim() };
  try {
    const result = operation
      ? await personnelApi.lifecycle(id, operation, body)
      : await personnelApi.change(id, {
          ...body,
          role: draftRole.value || null,
          active: draftActive.value,
          factory_ids: scope.value,
        });
    await apply(result);
  } catch (error) {
    if (disposed) return;
    operationError.value =
      error instanceof PersonnelError && error.status === 409
        ? '记录已变化或操作条件不满足，请关闭后刷新核对，重新提交。'
        : error instanceof PersonnelError && [401, 403].includes(error.status)
          ? '会话或管理权限已失效，请重新登录或检查授权。'
          : '变更未获确认，请刷新核对后重试。';
  } finally {
    busy.value = false;
    confirmation.value = undefined;
  }
}
function page(delta: number) {
  offset.value = Math.max(0, offset.value + delta);
  void load();
}
function historyPage(delta: number) {
  historyOffset.value = Math.max(0, historyOffset.value + delta);
  void history();
}
onMounted(load);
onUnmounted(() => {
  disposed = true;
  generation++;
  historyGeneration++;
  controller?.abort();
  historyController?.abort();
});
</script>
<template>
  <div class="people-module">
    <header class="settings-section-header">
      <div>
        <h2>人员管理</h2>
        <p>只维护三种角色与工厂范围，不从飞书部门自动授权。</p>
      </div>
      <button class="button secondary" :disabled="busy" @click="load">刷新人员</button>
    </header>
    <p v-if="account.synthetic" class="asset-source-notice synthetic">
      隔离测试环境 · 合成人员与授权
    </p>
    <p v-if="message" class="people-confirmed" role="status">{{ message }}</p>
    <div v-if="state === 'loading'" class="loading-state" role="status">正在查询人员与授权…</div>
    <EmptyState
      v-else-if="state === 'forbidden'"
      icon="ShieldCheck"
      title="仅集团负责人可管理人员"
      description="当前身份不能查看人员列表或修改他人授权。"
    />
    <EmptyState
      v-else-if="state === 'expired'"
      icon="ShieldCheck"
      title="登录已过期"
      description="请重新登录后管理人员。"
      ><RouterLink
        class="button primary"
        :to="{ path: loginTarget(route.path), query: { return_to: route.fullPath } }"
        >前往登录</RouterLink
      ></EmptyState
    >
    <EmptyState
      v-else-if="state === 'error'"
      icon="Unplug"
      title="人员查询失败"
      description="服务暂不可用，请重试；不会展示为无人员。"
    />
    <template v-else>
      <div class="table-scroll">
        <table class="people-table">
          <caption class="sr-only">
            人员管理列表
          </caption>
          <thead>
            <tr>
              <th>人员</th>
              <th>飞书绑定</th>
              <th>管理角色</th>
              <th>工厂范围</th>
              <th>账号状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="person in people?.items" :key="person.id" :data-person-id="person.id">
              <td data-label="人员">
                <strong>{{ person.display_name }}</strong>
              </td>
              <td data-label="飞书绑定">{{ bindingLabel(person.feishu_binding) }}</td>
              <td data-label="管理角色">{{ roleLabel(person.role) }}</td>
              <td data-label="工厂范围">
                {{
                  person.role === 'group_lead'
                    ? '全部加工厂'
                    : person.factories.map((f) => f.name).join('、') || '待授权'
                }}
              </td>
              <td data-label="账号状态">
                <span class="status-pill neutral">{{ person.active ? '启用' : '停用' }}</span>
              </td>
              <td data-label="操作">
                <div class="people-row-actions">
                  <button class="text-button" :disabled="busy" @click="edit(person)">
                    管理授权</button
                  ><button class="text-button" :disabled="busy" @click="showHistory(person)">
                    变更记录
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-if="!people?.items.length"
        icon="CircleUserRound"
        title="暂无人员记录"
        description="仅展示已通过可信身份流程建立的本地账号，不读取通讯录。"
      />
      <footer class="list-footer">
        <span>共 {{ people?.total ?? 0 }} 个账号</span>
        <div class="pagination">
          <button class="button secondary" :disabled="offset === 0 || busy" @click="page(-20)">
            上一页</button
          ><button
            class="button secondary"
            :disabled="!people || offset + people.items.length >= people.total || busy"
            @click="page(20)"
          >
            下一页
          </button>
        </div>
      </footer>
    </template>
    <p class="settings-hint">
      停用、角色或工厂变化会撤销旧会话，人员需重新登录。通讯录事件与定期对账尚未接入；可在此人工受控停用。普通员工保留待授权状态，不增加第四种管理角色。
    </p>
    <AppOverlay
      v-model:open="open"
      :title="mode === 'edit' ? '人员授权' : '权限变更记录'"
      kind="drawer"
    >
      <p v-if="account.synthetic" class="asset-source-notice synthetic">
        隔离测试环境 · 合成人员与授权
      </p>
      <template v-if="selected && mode === 'edit'">
        <h3>{{ selected.display_name }}</h3>
        <p class="form-description">
          飞书{{
            bindingLabel(selected.feishu_binding)
          }}。修改必须填写原因；最后一位启用的集团负责人不可移除。
        </p>
        <form class="people-form" @submit.prevent="submit()">
          <label class="form-field"
            >管理角色<select v-model="draftRole" aria-label="管理角色" :disabled="busy">
              <option value="">待授权（无管理角色）</option>
              <option v-for="(label, role) in roleNames" :key="role" :value="role">
                {{ label }}
              </option>
            </select></label
          >
          <label class="people-checkbox"
            ><input v-model="draftActive" type="checkbox" :disabled="busy" />账号启用</label
          >
          <fieldset
            v-if="['engineer', 'factory_equipment_admin'].includes(draftRole)"
            class="people-scopes"
          >
            <legend>授权工厂</legend>
            <p class="inline-hint">
              {{
                draftRole === 'factory_equipment_admin'
                  ? '加工厂设备管理员至多选择一个工厂。'
                  : '工程师可选择一个或多个工厂。'
              }}没有有效范围时保持待授权。
            </p>
            <label v-for="factory in factories" :key="factory.id" class="people-checkbox"
              ><input
                v-model="scope"
                :value="factory.id"
                type="checkbox"
                :disabled="
                  busy ||
                  (draftRole === 'factory_equipment_admin' &&
                    scope.length >= 1 &&
                    !scope.includes(factory.id))
                "
              />{{ factory.name }}</label
            >
          </fieldset>
          <p v-else class="form-description">
            {{
              draftRole === 'group_lead'
                ? '集团负责人可查看全部启用加工厂，并管理人员授权。'
                : '待授权账号不能查询设备台账。'
            }}
          </p>
          <label class="form-field"
            >变更原因<textarea
              v-model="reason"
              aria-label="变更原因"
              maxlength="300"
              minlength="2"
              required
              :disabled="busy"
              placeholder="例如：调厂、转岗或离职停用"
            />
          </label>
          <p v-if="operationError" class="identity-error" role="alert">{{ operationError }}</p>
          <button class="button primary" type="submit" :disabled="busy || !hasReason || !changed">
            {{ busy ? '正在提交…' : '保存授权' }}
          </button>
          <div class="people-lifecycle">
            <h3>会话与身份</h3>
            <p>解绑飞书会拒绝该身份再次登录，不会自动重绑；纠错需要受控人工核实。</p>
            <button
              class="button secondary"
              type="button"
              :disabled="busy || !hasReason"
              @click="confirmation = 'revoke-sessions'"
            >
              撤销全部会话</button
            ><button
              class="button secondary"
              type="button"
              :disabled="busy || !hasReason || selected.feishu_binding !== 'bound'"
              @click="confirmation = 'unbind-feishu'"
            >
              解绑飞书
            </button>
          </div>
          <div v-if="confirmation" class="identity-pending" role="alert">
            <p>
              {{
                confirmation === 'unbind-feishu'
                  ? '确认解绑此人员的飞书身份，并撤销会话？'
                  : '确认撤销此人员的全部平台会话？'
              }}
            </p>
            <button
              class="button primary"
              type="button"
              :disabled="busy"
              @click="submit(confirmation)"
            >
              确认操作</button
            ><button
              class="text-button"
              type="button"
              :disabled="busy"
              @click="confirmation = undefined"
            >
              取消
            </button>
          </div>
        </form>
      </template>
      <template v-else-if="selected">
        <h3>{{ selected.display_name }}</h3>
        <p class="form-description">追加保存的权限事实，管理人员不能修改或删除历史。</p>
        <div v-if="historyState === 'loading'" class="loading-state" role="status">
          正在查询变更记录…
        </div>
        <p v-else-if="historyState === 'error'" class="identity-error" role="alert">
          记录查询失败，请关闭后重试。
        </p>
        <ol v-else class="people-history">
          <li v-for="record in records?.items" :key="record.id">
            <time>{{ new Date(record.occurred_at).toLocaleString('zh-CN') }}</time
            ><strong>{{ record.details?.reason || '受控权限变更' }}</strong
            ><template v-if="record.details"
              ><p>
                角色：{{ roleLabel(record.details.before.role) }} →
                {{ roleLabel(record.details.after.role) }}
              </p>
              <p>
                工厂：{{ factoryNames(record.details.before.factory_ids) }} →
                {{ factoryNames(record.details.after.factory_ids) }}
              </p>
              <p>
                状态：{{ record.details.before.active ? '启用' : '停用' }} →
                {{ record.details.after.active ? '启用' : '停用' }}
              </p>
              <p>
                飞书：{{ bindingLabel(record.details.before.feishu_binding) }} →
                {{ bindingLabel(record.details.after.feishu_binding) }}
              </p></template
            >
          </li>
        </ol>
        <p v-if="historyState === 'loaded' && !records?.items.length">暂无权限变更记录</p>
        <div v-if="records" class="pagination">
          <button
            class="button secondary"
            :disabled="historyOffset === 0"
            @click="historyPage(-20)"
          >
            较新记录</button
          ><button
            class="button secondary"
            :disabled="historyOffset + records.items.length >= records.total"
            @click="historyPage(20)"
          >
            较早记录
          </button>
        </div>
      </template>
    </AppOverlay>
  </div>
</template>
