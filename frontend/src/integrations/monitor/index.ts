import type { RouteRecordRaw } from 'vue-router';
import { enableMonitorPortal } from '../../shared/api-path';

export const operationsModules = [
  { path: 'assets', title: '设备台账', icon: 'Boxes', ready: true },
  { path: 'inspections', title: '人员巡检', icon: 'ClipboardCheck', ready: false },
  { path: 'issues', title: '问题报修', icon: 'MessageSquareWarning', ready: false },
  { path: 'work-orders', title: '维修工单', icon: 'Wrench', ready: false },
  { path: 'maintenance', title: '设备保养', icon: 'CalendarDays', ready: false },
  { path: 'inventory', title: '备品备件', icon: 'Package', ready: false },
  { path: 'analytics', title: '统计分析', icon: 'BarChart3', ready: false },
  { path: 'settings', title: '运维设置', icon: 'Settings2', ready: true },
] as const;

export function createOperationsRoutes(options: { connected?: boolean } = {}): RouteRecordRaw[] {
  enableMonitorPortal();
  return [{
    path: '/operations',
    component: () => import('./OperationsPortal.vue'),
    props: { connected: options.connected !== false },
    redirect: '/operations/assets',
    meta: { title: '设备运维' },
    children: [
      ...operationsModules.map(item => ({
        path: item.path, name: `operations-${item.path}`, meta: { title: item.title },
        component: item.path === 'assets' ? () => import('../../modules/assets/AssetsLivePage.vue')
          : item.path === 'settings' ? () => import('./PortalSettings.vue')
            : () => import('./PendingModule.vue'),
      })),
      { path: 'assets/:id', name: 'operations-asset-detail',
        component: () => import('./PortalAssetDetail.vue'), meta: { title: '设备详情' } },
      { path: 'from-monitor', name: 'operations-from-monitor',
        component: () => import('./FromMonitor.vue'), meta: { title: '运维档案关联' } },
      { path: 'access', component: () => import('./PendingModule.vue'),
        meta: { title: '个人身份接入' } },
      { path: ':pathMatch(.*)*', component: () => import('./PendingModule.vue'),
        meta: { title: '页面未找到' } },
    ],
  }];
}
