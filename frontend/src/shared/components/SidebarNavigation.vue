<script setup lang="ts">
import { useRoute } from 'vue-router';
import { navigation, navigationGroups } from '../../app/navigation';
import AppIcon from './AppIcon.vue';
const route = useRoute();
</script>
<template>
  <div class="sidebar-content">
    <RouterLink to="/workbench" class="brand"
      ><span class="brand-icon"><AppIcon name="Boxes" :size="25" /></span
      ><span><strong>工厂设备运维</strong><small>FACTORY OPERATIONS</small></span></RouterLink
    >
    <nav aria-label="主导航" class="sidebar-nav">
      <div v-for="group in navigationGroups" :key="group" class="nav-group">
        <p>{{ group }}</p>
        <RouterLink
          v-for="item in navigation.filter((item) => item.group === group)"
          :key="item.id"
          :to="`/${item.id}`"
          :class="{ active: route.meta.moduleId === item.id }"
          ><AppIcon :name="item.icon" :size="19" /><span>{{ item.title }}</span
          ><span v-if="route.meta.moduleId === item.id" class="nav-active-dot"></span
        ></RouterLink>
      </div>
    </nav>
    <div class="sidebar-footer">
      <RouterLink to="/m/home"
        ><AppIcon name="Smartphone" :size="18" /><span>移动工作台</span
        ><AppIcon name="ArrowUpRight" :size="15"
      /></RouterLink>
      <div class="sidebar-stage">
        <span class="status-dot"></span>M0.5 <span>平台框架预览</span>
      </div>
    </div>
  </div>
</template>
