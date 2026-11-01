<script setup lang="ts">
import AppIcon from '../../shared/components/AppIcon.vue';
</script>
<template>
  <header class="mobile-page-heading">
    <span class="eyebrow">MY WORKSPACE</span>
    <h1>我的</h1>
    <p>个人身份、工厂范围与平台入口。</p>
  </header>
  <section class="panel profile-card">
    <span class="profile-symbol"><AppIcon name="CircleUserRound" :size="33" /></span>
    <div>
      <h2>身份服务尚未接入</h2>
      <p>未登录 · 未分配角色或工厂</p>
    </div>
    <span class="status-pill neutral">预览</span>
  </section>
  <section class="panel profile-menu">
    <RouterLink to="/m/settings?tab=organization"
      ><AppIcon name="Building2" />
      <div><strong>组织与工厂</strong><small>工厂服务未接入</small></div>
      <AppIcon name="ChevronRight" :size="17" /></RouterLink
    ><RouterLink to="/m/settings?tab=roles"
      ><AppIcon name="ShieldCheck" />
      <div><strong>角色与范围</strong><small>查看三种管理角色的设计预留</small></div>
      <AppIcon name="ChevronRight" :size="17" /></RouterLink
    ><RouterLink to="/m/settings?tab=integrations"
      ><AppIcon name="Unplug" />
      <div><strong>集成设置</strong><small>飞书与冷库监控未连接</small></div>
      <AppIcon name="ChevronRight" :size="17" /></RouterLink
    ><RouterLink to="/workbench"
      ><AppIcon name="Monitor" />
      <div><strong>打开管理端</strong><small>适合电脑与大屏设备</small></div>
      <AppIcon name="ArrowUpRight" :size="17"
    /></RouterLink>
  </section>
  <div class="profile-boundary">
    <AppIcon name="Fingerprint" :size="23" />
    <p>本轮没有模拟登录、角色切换或虚假权限验证。身份与授权将由后续后端服务提供。</p>
  </div>
</template>
