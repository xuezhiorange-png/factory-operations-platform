import type { FactoryScope } from '../../shared/contracts';

// Future backend contracts, never a local login/authorization implementation.
export type BusinessManagementRole = 'group_lead' | 'engineer' | 'factory_equipment_admin';
export interface FactorySummary {
  id: string;
  title: string;
}
export interface ManagementGrant {
  userId: string;
  role: BusinessManagementRole;
  factoryIds: readonly string[];
}
export interface SettingsReadPort {
  listAuthorizedFactories(): Promise<readonly FactorySummary[]>;
  listGrants(scope: FactoryScope): Promise<readonly ManagementGrant[]>;
}
