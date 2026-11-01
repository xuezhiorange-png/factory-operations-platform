<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { account, accountLabel, roleNames, logout, loginTarget } from './account';
const route = useRoute();
const router = useRouter();
const busy = ref(false);
const failed = ref(false);
async function exit() {
  busy.value = true;
  failed.value = false;
  try {
    await logout();
    await router.replace({
      path: loginTarget(route.path),
      query: { return_to: route.fullPath },
    });
  } catch {
    failed.value = true;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="identity-panel">
    <span v-if="account.synthetic" class="asset-source-notice synthetic"
      >隔离测试环境 · 合成身份</span
    >
    <h2>{{ accountLabel }}</h2>
    <template v-if="account.user">
      <p>
        {{ account.user.role ? roleNames[account.user.role] : '尚未分配管理角色' }}
      </p>
      <p v-if="account.status === 'pending'" class="identity-pending" role="status">
        账号待授权。请联系集团负责人分配角色与工厂范围。
      </p>
      <h3>可访问的加工厂</h3>
      <ul class="identity-factories">
        <li v-for="factory in account.user.factories" :key="factory.id">
          {{ factory.name }}
        </li>
      </ul>
      <p v-if="!account.user.factories.length">尚无工厂授权</p>
      <button class="button secondary" :disabled="busy" @click="exit">
        {{ busy ? '正在退出…' : '退出登录' }}
      </button>
      <p v-if="failed" class="identity-error" role="alert">
        退出失败，服务尚未确认会话撤销，请重试。
      </p>
    </template>
    <RouterLink
      v-else
      class="button primary"
      :to="{
        path: loginTarget(route.path),
        query: { return_to: route.fullPath },
      }"
      >前往登录</RouterLink
    >
  </section>
</template>
