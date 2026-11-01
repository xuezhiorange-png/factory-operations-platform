import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'issues',
  title: '问题报修',
  english: 'ISSUE CENTER',
  description: '汇集现场问题与异常，清晰分诊，有序跟进。',
  icon: 'MessageSquareWarning',
  noun: '报修问题',
  action: '新建报修',
  stage: 'M3',
  columns: ['问题编号 / 标题', '关联设备 / 位置', '问题来源', '优先级', '处理状态', '操作'],
  tabs: ['全部问题', '待分诊', '处理中', '已归档'],
  filterLabel: '问题来源',
  filterOptions: ['员工报修', '巡检异常', '监控告警'],
  boundary: 'Issue 与维修工单独立，通过关联记录追溯每次报修与维修尝试；重复问题保留原始来源。',
  detailPath: 'issues/preview',
} satisfies ModuleConfig;
