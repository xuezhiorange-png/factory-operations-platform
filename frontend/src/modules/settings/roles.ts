export const managementRoles = [
  {
    code: 'GROUP_LEAD',
    name: '集团负责人',
    scope: '集团全部工厂',
    description: '集团汇总、授权管理、跨厂督办与独立验收。',
    icon: 'Building2',
  },
  {
    code: 'ENGINEER',
    name: '工程师',
    scope: '明确授权的一个或多个工厂',
    description: '设备维护、巡检组织、技术处理与维修协同。',
    icon: 'Wrench',
  },
  {
    code: 'FACTORY_EQUIPMENT_ADMIN',
    name: '加工厂设备管理员',
    scope: '本工厂',
    description: '设备建档、现场盘点、任务组织与资料整理。',
    icon: 'ClipboardCheck',
  },
] as const;
