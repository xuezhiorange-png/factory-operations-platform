import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'analytics',
  title: '统计分析',
  english: 'OPERATIONS INSIGHTS',
  description: '基于可信业务事实，逐步建立清晰的运维指标。',
  icon: 'BarChart3',
  noun: '分析报表',
  action: '新建分析报表',
  stage: 'M5',
  columns: ['报表名称', '统计范围', '统计周期', '数据口径', '更新时间', '操作'],
  tabs: ['运维概览', '设备分析', '巡检分析', '维修分析'],
  filterLabel: '统计周期',
  filterOptions: ['本周', '本月', '本季度'],
  boundary:
    '按明确口径汇总业务事件；没有可信时间轴或运行时长时，MTTR、MTBF 显示数据不足，不生成推测指标。',
} satisfies ModuleConfig;
