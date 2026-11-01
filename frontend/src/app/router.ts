import { ref } from 'vue';
import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router';
import DesktopLayout from '../shared/layouts/DesktopLayout.vue';
import MobileLayout from '../shared/layouts/MobileLayout.vue';

declare module 'vue-router' {
  interface RouteMeta {
    title: string;
    shell?: 'desktop' | 'mobile';
    moduleId?: string;
    parentTitle?: string;
    detail?: boolean;
    mobilePage?: string;
    mobileTab?: string;
  }
}
const modules = [
  {
    path: 'assets',
    title: '设备台账',
    component: () => import('../modules/assets/AssetsPage.vue'),
  },
  {
    path: 'inspections',
    title: '巡检管理',
    component: () => import('../modules/inspections/InspectionsPage.vue'),
  },
  {
    path: 'issues',
    title: '问题报修',
    component: () => import('../modules/issues/IssuesPage.vue'),
  },
  {
    path: 'work-orders',
    title: '维修工单',
    component: () => import('../modules/work-orders/WorkOrdersPage.vue'),
  },
  {
    path: 'maintenance',
    title: '设备保养',
    component: () => import('../modules/maintenance/MaintenancePage.vue'),
  },
  {
    path: 'inventory',
    title: '备品备件',
    component: () => import('../modules/inventory/InventoryPage.vue'),
  },
  {
    path: 'analytics',
    title: '统计分析',
    component: () => import('../modules/analytics/AnalyticsPage.vue'),
  },
  {
    path: 'settings',
    title: '系统设置',
    component: () => import('../modules/settings/SettingsPage.vue'),
  },
];
const details = [
  {
    path: 'assets/:id',
    moduleId: 'assets',
    parentTitle: '设备台账',
    title: '设备详情',
    component: () => import('../modules/assets/AssetDetail.vue'),
  },
  {
    path: 'inspections/:id',
    moduleId: 'inspections',
    parentTitle: '巡检管理',
    title: '巡检任务详情',
    component: () => import('../modules/inspections/InspectionTask.vue'),
  },
  {
    path: 'issues/:id',
    moduleId: 'issues',
    parentTitle: '问题报修',
    title: '报修详情',
    component: () => import('../modules/issues/IssueDetail.vue'),
  },
  {
    path: 'work-orders/:id',
    moduleId: 'work-orders',
    parentTitle: '维修工单',
    title: '维修工单详情',
    component: () => import('../modules/work-orders/WorkOrderDetail.vue'),
  },
];
function moduleRoutes(prefix: string): RouteRecordRaw[] {
  return [
    ...modules.map((item) => ({
      path: item.path,
      name: `${prefix}-${item.path}`,
      component: item.component,
      meta: {
        title: item.title,
        moduleId: item.path,
        mobileTab: ['inspections', 'work-orders', 'maintenance'].includes(item.path)
          ? 'tasks'
          : item.path === 'settings'
            ? 'me'
            : 'home',
      },
    })),
    ...details.map((item) => ({
      path: item.path,
      name: `${prefix}-${item.moduleId}-detail`,
      component: item.component,
      meta: {
        title: item.title,
        parentTitle: item.parentTitle,
        moduleId: item.moduleId,
        detail: true,
        mobileTab: ['inspections', 'work-orders'].includes(item.moduleId) ? 'tasks' : 'home',
      },
    })),
    {
      path: 'design-system',
      name: `${prefix}-design-system`,
      component: () => import('../modules/settings/DesignSystemPage.vue'),
      meta: { title: '界面组件规范', moduleId: 'settings', mobileTab: 'me' },
    },
    {
      path: ':pathMatch(.*)*',
      name: `${prefix}-not-found`,
      component: () => import('./NotFoundPage.vue'),
      meta: { title: '页面未找到', mobileTab: 'home' },
    },
  ];
}
export const router = createRouter({
  history: createWebHashHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (to.path === from.path) return false;
    return savedPosition ?? { top: 0 };
  },
  routes: [
    {
      path: '/',
      redirect: () => (window.matchMedia('(max-width: 760px)').matches ? '/m/home' : '/workbench'),
    },
    {
      path: '/',
      component: DesktopLayout,
      meta: { shell: 'desktop', title: '管理端' },
      children: [
        {
          path: 'workbench',
          name: 'pc-workbench',
          component: () => import('../modules/dashboard/WorkbenchPage.vue'),
          meta: { title: '工作台', moduleId: 'workbench' },
        },
        ...moduleRoutes('pc'),
      ],
    },
    {
      path: '/m',
      component: MobileLayout,
      redirect: '/m/home',
      meta: { shell: 'mobile', title: '移动工作台' },
      children: [
        {
          path: 'home',
          component: () => import('../modules/mobile/MobileHomePage.vue'),
          meta: { title: '移动工作台', mobilePage: 'home', mobileTab: 'home' },
        },
        {
          path: 'tasks',
          component: () => import('../modules/mobile/MobileTasksPage.vue'),
          meta: { title: '我的任务', mobilePage: 'tasks', mobileTab: 'tasks' },
        },
        {
          path: 'scan',
          component: () => import('../modules/mobile/MobileScanPage.vue'),
          meta: { title: '设备扫码', mobilePage: 'scan', mobileTab: 'scan' },
        },
        {
          path: 'messages',
          component: () => import('../modules/mobile/MobileMessagesPage.vue'),
          meta: { title: '消息中心', mobilePage: 'messages', mobileTab: 'messages' },
        },
        {
          path: 'me',
          component: () => import('../modules/mobile/MobileMePage.vue'),
          meta: { title: '我的', mobilePage: 'me', mobileTab: 'me' },
        },
        ...moduleRoutes('mobile'),
      ],
    },
  ],
});
export const navigating = ref(false);
router.beforeEach(() => {
  navigating.value = true;
});
router.afterEach((to) => {
  document.title = `${to.meta.title} · 加工厂设备运维`;
  navigating.value = false;
});
router.onError(() => {
  navigating.value = false;
});
