<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { account, refreshAccount, startLogin, internalTarget } from './account';
import AppIcon from '../../shared/components/AppIcon.vue';
const route = useRoute();
const router = useRouter();
const mobile = computed(() => route.path.startsWith('/m/'));
const target = computed(() =>
  internalTarget(route.query.return_to, mobile.value ? '/m/home' : '/workbench'),
);
const busy = ref(false);
const failed = ref(route.query.status === 'failed');
async function login() {
  busy.value = true;
  failed.value = false;
  try {
    await startLogin(target.value, mobile.value ? 'h5' : 'pc');
  } catch {
    failed.value = true;
    busy.value = false;
  }
}
async function retry() {
  failed.value = false;
  const { status: _status, reason: _reason, ...query } = route.query;
  await router.replace({ query });
  await refreshAccount();
}
onMounted(async () => {
  const originalPath = route.fullPath;
  await refreshAccount();
  if (route.fullPath !== originalPath) return;
  if (account.user) {
    await router.replace(target.value);
    return;
  }
  if (mobile.value && route.query.auto === '1' && account.configured && !failed.value)
    await login();
});
</script>
<template>
  <section class="identity-login">
    <div class="panel identity-login-card">
      <span class="identity-login-icon"><AppIcon name="Fingerprint" :size="32" /></span>
      <span class="eyebrow">FACTORY OPERATIONS</span>
      <h1>{{ mobile ? '飞书工作台登录' : '登录设备运维平台' }}</h1>
      <p>通过企业飞书确认身份，设备范围由本平台授权。</p>
      <p v-if="account.synthetic" class="asset-source-notice synthetic">隔离测试环境 · 合成身份</p>
      <div v-if="account.status === 'loading'" role="status">正在检查登录状态…</div>
      <p v-else-if="account.status === 'error'" class="identity-error" role="alert">
        身份服务异常，请稍后重试。
      </p>
      <p
        v-else-if="
          failed &&
          ['storage_unavailable', 'identity_provider_unavailable'].includes(
            String(route.query.reason),
          )
        "
        class="identity-error"
        role="alert"
      >
        身份服务异常，请稍后重新发起登录。
      </p>
      <p
        v-else-if="failed && route.query.reason === 'permission_denied'"
        class="identity-error"
        role="alert"
      >
        账号已停用或身份绑定已撤销，请联系集团负责人。
      </p>
      <p v-else-if="failed" class="identity-error" role="alert">
        登录未完成。凭证可能无效、过期或已使用，请重新发起登录。
      </p>
      <p v-else-if="account.status === 'expired' || route.query.status === 'expired'" role="status">
        登录已过期或被撤销，请重新登录。
      </p>
      <p v-else role="status">尚未登录</p>
      <p v-if="!account.configured && account.status !== 'loading'" class="inline-hint">
        飞书真实认证未配置，当前通道关闭。请联系平台负责人完成受控配置。
      </p>
      <button
        class="button primary"
        :disabled="busy || !account.configured || account.status === 'loading'"
        @click="login"
      >
        <AppIcon name="ArrowUpRight" :size="18" />{{ busy ? '正在前往飞书…' : '通过飞书登录' }}
      </button>
      <button class="text-button" :disabled="busy" @click="retry">重新检查服务</button>
      <p class="identity-login-note">
        首次登录后若未分配角色及工厂，将显示“账号待授权”。无需在此输入密码或密钥。
      </p>
    </div>
  </section>
</template>
