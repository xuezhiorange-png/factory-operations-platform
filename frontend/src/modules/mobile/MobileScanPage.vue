<script setup lang="ts">
import AppIcon from '../../shared/components/AppIcon.vue';
</script>
<template>
  <header class="mobile-page-heading">
    <span class="eyebrow">SCAN & CONNECT</span>
    <h1>扫码进入设备</h1>
    <p>计划通过设备标签，连接档案与现场任务。</p>
  </header>
  <section class="panel scan-panel">
    <div class="scan-frame" aria-hidden="true">
      <span></span><AppIcon name="QrCode" :size="48" /><span></span>
    </div>
    <span class="status-pill neutral">相机与扫码未接入</span>
    <h2>当前不会请求相机权限</h2>
    <p>此处仅预留扫码入口，不生成二维码，也不模拟识别设备。</p>
    <button class="button primary" disabled>
      <AppIcon name="QrCode" :size="18" />开始扫码 · 待开发</button
    ><RouterLink to="/m/assets" class="button secondary"
      ><AppIcon name="Search" :size="17" />前往设备台账</RouterLink
    >
  </section>
  <div class="mobile-info-note">
    <AppIcon name="Info" :size="19" />
    <p>后续扫码仍需身份认证与工厂范围校验。标签本身不授予设备访问权限。</p>
  </div>
</template>
