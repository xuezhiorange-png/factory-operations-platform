import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'assets',
  title: '设备台账',
  english: 'ASSET REGISTER',
  description: '设备全生命周期档案，连接位置、巡检与维修履历。',
  icon: 'Boxes',
  noun: '设备',
  action: '新增设备',
  stage: 'M1',
  columns: ['设备编号 / 名称', '分类', '所属工厂 / 位置', '生命周期', '负责人', '操作'],
  tabs: ['全部设备', '在用设备', '停用 / 封存', '已报废'],
  filterLabel: '设备分类',
  filterOptions: ['制冷设备', '生产加工', '公用工程'],
  boundary: '资产、功能机位、位置与测点分别建模；安装、调拨和编码变更保留有效期历史。',
  detailPath: 'assets/preview',
} satisfies ModuleConfig;
