import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'inspections',
  title: '巡检管理',
  english: 'INSPECTION CENTER',
  description: '从计划到执行，让每一次检查都有标准、有记录。',
  icon: 'ClipboardCheck',
  noun: '巡检任务',
  action: '创建巡检计划',
  stage: 'M2',
  columns: ['任务名称', '巡检对象', '计划时段', '执行人', '任务状态', '操作'],
  tabs: ['巡检任务', '巡检计划', '模板管理'],
  filterLabel: '任务状态',
  filterOptions: ['待执行', '进行中', '已提交', '已逾期'],
  boundary: '按模板版本、计划、批次和设备任务逐步接入，保留漏检、晚检、代检和补录事实。',
  detailPath: 'inspections/preview',
} satisfies ModuleConfig;
