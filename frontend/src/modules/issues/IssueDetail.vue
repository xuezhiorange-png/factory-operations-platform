<script setup lang="ts">
import DetailPage from '../../shared/components/DetailPage.vue';
import type { DetailConfig } from '../../shared/types';
const config = {
  title: '报修详情',
  parent: '问题报修',
  moduleId: 'issues',
  icon: 'MessageSquareWarning',
  description: '汇集问题描述、现场证据与关联维修记录。',
  tabs: ['问题信息', '现场证据', '分诊记录', '关联工单'],
  fields: [
    '问题编号',
    '问题标题',
    '所属工厂',
    '设备 / 位置',
    '报修来源',
    '问题优先级',
    '报修时间',
    '报修人',
    '分诊状态',
    '关联工单',
  ],
  action: '问题分诊',
  sideTitle: '处理时间线',
  sideDescription: '上报、分诊和处理事件尚未接入。',
} satisfies DetailConfig;
</script>
<template><DetailPage :config="config" /></template>
