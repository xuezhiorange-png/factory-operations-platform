<script setup lang="ts">
import DetailPage from '../../shared/components/DetailPage.vue';
import type { DetailConfig } from '../../shared/types';
const config = {
  title: '巡检任务详情',
  parent: '巡检管理',
  moduleId: 'inspections',
  icon: 'ClipboardCheck',
  description: '按检查标准记录执行过程，保留每次检查的真实状态。',
  tabs: ['任务概况', '检查项目', '执行记录', '异常关联'],
  fields: [
    '任务编号',
    '任务名称',
    '所属工厂',
    '关联设备 / 位置',
    '模板版本',
    '计划时间',
    '任务截止',
    '被指派执行人',
    '实际执行人',
    '任务状态',
  ],
  action: '开始巡检',
  sideTitle: '执行进度',
  sideDescription: '任务指派、检查结果与提交时间尚未接入。',
} satisfies DetailConfig;
</script>
<template><DetailPage :config="config" /></template>
