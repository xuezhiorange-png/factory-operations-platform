import type { AssetCategory, AssetStatus } from './contracts';
export const categories: Record<AssetCategory, string> = {
  refrigeration: '制冷设备',
  processing: '生产加工',
  utilities: '公用工程',
  other: '其他',
};
export const statuses: Record<AssetStatus, string> = {
  pending: '待验收 / 安装',
  in_use: '在用',
  inactive: '停用 / 封存',
  retired: '已报废',
};
