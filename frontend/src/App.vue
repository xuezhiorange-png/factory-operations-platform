<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { checkHealth } from './api/health'

type BackendStatus = 'checking' | 'online' | 'offline'
const backendStatus = ref<BackendStatus>('checking')

onMounted(async () => {
  try {
    backendStatus.value = await checkHealth() ? 'online' : 'offline'
  } catch {
    backendStatus.value = 'offline'
  }
})
</script>

<template>
  <main class="shell">
    <header class="masthead">
      <div class="brand-mark" aria-hidden="true">设</div>
      <div class="brand-title">
        <strong>加工厂设备运维管理平台</strong>
        <span>Factory Operations Platform</span>
      </div>
      <span class="stage">M0 · 工程初始化</span>
    </header>
    <section class="hero">
      <p class="eyebrow">工程基础阶段</p>
      <h1>统一设备资产，连接巡检与维修</h1>
      <p class="summary">当前仅为工程初始化页面，没有接入真实工厂、设备、巡检或工单数据。</p>
      <div class="status" role="status" aria-live="polite">
        <span class="dot" :class="backendStatus" aria-hidden="true"></span>
        后端健康检查：{{ backendStatus === 'online' ? '已连接' : backendStatus === 'checking' ? '检查中' : '未连接' }}
      </div>
    </section>
    <section class="modules" aria-label="规划中的业务模块">
      <article v-for="item in ['设备台账', '巡检管理', '问题报修', '维修工单', '飞书集成', '监控只读联动']" :key="item">
        <div class="module-name">{{ item }}</div>
        <div class="module-state">规划中 · 尚未开发</div>
      </article>
    </section>
    <footer>本页面不可用于生产运维或操作现场设备。</footer>
  </main>
</template>
