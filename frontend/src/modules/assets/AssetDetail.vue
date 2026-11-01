<script setup lang="ts">
import { useRoute } from 'vue-router';
import { assetsApiEnabled } from '../../app/features';
import AssetLiveDetail from './AssetLiveDetail.vue';
import DetailPage from '../../shared/components/DetailPage.vue';
import type { DetailConfig } from '../../shared/types';
const route = useRoute();
const config = {
  title: '设备详情',
  parent: '设备台账',
  moduleId: 'assets',
  icon: 'Boxes',
  description: '设备资料、安装位置与运维履历的统一入口。',
  tabs: ['基础档案', '安装与位置', '巡检记录', '问题与工单', '资料附件', '变更履历'],
  fields: [
    '设备编号',
    '设备名称',
    '设备分类',
    '归属工厂',
    '厂家 / 型号',
    '出厂编号',
    '功能机位',
    '物理位置',
    '生命周期',
    '设备负责人',
    '投运日期',
    '重要等级',
  ],
  action: '编辑档案',
  sideTitle: '设备二维码',
  sideDescription: '标签生成与扫码入口将在台账接入后启用。',
} satisfies DetailConfig;
</script>
<template>
  <AssetLiveDetail
    v-if="assetsApiEnabled && route.params.id !== 'preview'"
    :config="config"
  /><DetailPage v-else :config="config" />
</template>
