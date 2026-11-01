import type { ModuleConfig } from '../../shared/types';

export const config = {
  id: 'work-orders',
  title: '维修工单',
  english: 'WORK ORDER CENTER',
  description: '连接派工、维修与独立验收，形成完整处理闭环。',
  icon: 'Wrench',
  noun: '维修工单',
  action: '创建维修工单',
  stage: 'M3',
  columns: ['工单编号 / 标题', '关联设备', '执行人', '计划时间', '工单状态', '操作'],
  tabs: ['全部工单', '待派工', '维修中', '待验收', '已关闭'],
  filterLabel: '工单状态',
  filterOptions: ['待派工', '待接单', '维修中', '待验收', '已关闭'],
  boundary:
    '接入持久化状态机、实际维修人记录、幂等提交与事务审计；任何角色不得验收本人维修的工单。',
  detailPath: 'work-orders/preview',
} satisfies ModuleConfig;
