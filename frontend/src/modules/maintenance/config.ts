import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'maintenance',
  title: '设备保养',
  english: 'PREVENTIVE MAINTENANCE',
  description: '提前安排维护周期，把保养融入日常运维。',
  icon: 'CalendarDays',
  noun: '保养计划',
  action: '创建保养计划',
  stage: 'M4',
  columns: ['计划名称', '适用设备', '保养周期', '下次执行时间', '计划状态', '操作'],
  tabs: ['保养计划', '保养任务', '保养模板'],
  filterLabel: '计划状态',
  filterOptions: ['待启用', '执行中', '已暂停'],
  boundary:
    '按时间、运行小时或作业次数规划保养；没有可信计量数据时不推算运行小时，延期和取消保留原因。',
} satisfies ModuleConfig;
