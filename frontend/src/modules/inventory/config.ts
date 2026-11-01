import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'inventory',
  title: '备品备件',
  english: 'PARTS & INVENTORY',
  description: '聚焦维修领用与归还，让备件流转清楚可追溯。',
  icon: 'Package',
  noun: '备品备件',
  action: '新增备件',
  stage: 'M4',
  columns: ['备件编号 / 名称', '规格型号', '仓库', '可用数量', '库存状态', '操作'],
  tabs: ['备件台账', '领退记录', '库存流水'],
  filterLabel: '库存状态',
  filterOptions: ['正常', '低于下限', '待盘点'],
  boundary: '先确认 ERP 与库存数据责任方，再接入工单关联的轻量领退流水；库存变化不可物理删除。',
} satisfies ModuleConfig;
