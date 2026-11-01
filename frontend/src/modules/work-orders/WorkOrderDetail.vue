<script setup lang="ts">
import DetailPage from '../../shared/components/DetailPage.vue';
import type { DetailConfig } from '../../shared/types';
const config = {
  title: '维修工单详情',
  parent: '维修工单',
  moduleId: 'work-orders',
  icon: 'Wrench',
  description: '连接维修执行、现场复测与独立验收的完整记录。',
  tabs: ['工单概况', '维修过程', '材料与工时', '复测与验收', '操作履历'],
  fields: [
    '工单编号',
    '工单标题',
    '所属工厂',
    '关联设备',
    '问题来源',
    '工单状态',
    '被指派执行人',
    '实际维修人',
    '计划时间',
    '停机时间',
    '完工时间',
    '验收人',
  ],
  action: '提交完工',
  sideTitle: '工单时间线',
  sideDescription: '派工、接单、维修和独立验收尚未接入。',
} satisfies DetailConfig;
</script>
<template><DetailPage :config="config" /></template>
