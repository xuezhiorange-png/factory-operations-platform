import type { IconName } from '../shared/icons';
export interface NavigationItem {
  id: string;
  title: string;
  icon: IconName;
  group: string;
}
export const navigation: NavigationItem[] = [
  { id: 'workbench', title: '工作台', icon: 'LayoutDashboard', group: '工作空间' },
  { id: 'assets', title: '设备台账', icon: 'Boxes', group: '设备运维' },
  { id: 'inspections', title: '巡检管理', icon: 'ClipboardCheck', group: '设备运维' },
  { id: 'issues', title: '问题报修', icon: 'MessageSquareWarning', group: '设备运维' },
  { id: 'work-orders', title: '维修工单', icon: 'Wrench', group: '设备运维' },
  { id: 'maintenance', title: '设备保养', icon: 'CalendarDays', group: '运维支持' },
  { id: 'inventory', title: '备品备件', icon: 'Package', group: '运维支持' },
  { id: 'analytics', title: '统计分析', icon: 'BarChart3', group: '运维支持' },
  { id: 'settings', title: '系统设置', icon: 'Settings2', group: '平台管理' },
];
export const navigationGroups = [...new Set(navigation.map((item) => item.group))];
