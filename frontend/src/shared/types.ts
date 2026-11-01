import type { IconName } from './icons';

export interface ModuleConfig {
  id: string;
  title: string;
  english: string;
  description: string;
  icon: IconName;
  noun: string;
  action: string;
  stage: string;
  columns: string[];
  tabs: string[];
  filterLabel: string;
  filterOptions: string[];
  detailPath?: string;
  boundary: string;
}
export interface DetailConfig {
  title: string;
  parent: string;
  moduleId: string;
  icon: IconName;
  description: string;
  tabs: string[];
  fields: string[];
  action: string;
  sideTitle: string;
  sideDescription: string;
}
