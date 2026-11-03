<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { account, clearAccount, refreshAccount, roleNames } from '../../modules/identity/account';
import AppIcon from '../../shared/components/AppIcon.vue';
import { operationsModules } from './index';
import './portal.css';
const props = withDefaults(defineProps<{ connected?: boolean }>(), { connected: true });
const route = useRoute();
const checking = ref(true);
let generation = 0;
async function check() {
  if (!props.connected) { generation++; clearAccount(); checking.value = false; return; }
  const current = ++generation;
  checking.value = true;
  await refreshAccount();
  if (current === generation) checking.value = false;
}
watch([() => route.fullPath, () => props.connected], check, { immediate: true });
onUnmounted(() => { generation++; clearAccount(); });
</script>
<template>
  <div class="operations-portal">
    <header class="operations-heading"><div><p>冷库监控 / 设备运维</p><h1>设备运维</h1></div>
      <div class="operations-identity"><AppIcon name="ShieldCheck" :size="17" />
        <span v-if="account.user && !checking">{{ account.user.display_name }}<small>{{ account.user.role ? roleNames[account.user.role] : '待授权' }}</small></span>
        <span v-else>{{ connected ? '个人身份校验' : '运维待接入' }}</span>
        <button type="button" class="icon-button" title="重新校验运维权限" aria-label="重新校验运维权限" :disabled="checking" @click="check"><AppIcon name="ArrowRight" :size="17" /></button>
      </div>
    </header>
    <nav class="operations-modules" aria-label="设备运维模块">
      <RouterLink v-for="item in operationsModules" :key="item.path" :to="`/operations/${item.path}`" :class="{ selected: route.path.startsWith(`/operations/${item.path}`) }"><AppIcon :name="item.icon" :size="17" /><span>{{ item.title }}</span><small v-if="!item.ready">待开发</small></RouterLink>
    </nav>
    <div v-if="checking" class="operations-access" role="status" aria-busy="true"><AppIcon name="LoaderCircle" class="spin" /><p>正在校验运维权限…</p></div>
    <div v-else-if="!connected || account.status !== 'authorized'" class="operations-access" role="status">
      <AppIcon name="ShieldCheck" :size="30" />
      <h2>{{ !connected ? '设备运维待接入' : account.status === 'error' ? '运维身份服务不可用' : account.status === 'pending' ? '运维账号待授权' : '统一登录待接入' }}</h2>
      <p>{{ !connected ? '当前仅开放入口，个人登录和设备数据尚未接通。' : account.status === 'pending' ? '请由集团负责人分配角色和工厂权限。' : account.status === 'error' ? '暂时无法校验个人身份，请稍后重试。' : '监控账号不等同于个人运维身份，当前未显示运维数据。' }}</p>
      <button v-if="connected" class="button secondary" @click="check">重新检查</button><RouterLink to="/">返回监控总览</RouterLink>
    </div>
    <main v-else class="operations-body"><RouterView /></main>
  </div>
</template>
