import type { FactoryScope, IntegrationState } from '../../shared/contracts';

export interface IntegrationDescriptor {
  id: 'feishu' | 'monitoring';
  state: IntegrationState;
}
export const integrations: readonly IntegrationDescriptor[] = [
  { id: 'feishu', state: 'not-connected' },
  { id: 'monitoring', state: 'not-connected' },
];
// No SDK import, credential storage, login/session stub or external request in M0.5.
export interface MonitoringReadPort {
  readSummary(
    scope: FactoryScope,
    bindingId: string,
  ): Promise<{
    observedAt: string;
    sourceId: string;
    availability: 'available' | 'stale' | 'offline';
  }>;
}
// Feishu login must be exchanged and validated by the future backend, not trusted by this shell.
export interface FeishuEntryPort {
  getEntryCapability(): Promise<{ available: boolean; reason?: string }>;
}
