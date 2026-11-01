import type { FactoryReadPort } from '../../shared/contracts';

/** Proposed read contract; no API adapter or sample business records in M0.5. */
export interface InspectionTaskSummary {
  id: string;
  factoryId: string;
  title: string;
  version: number;
}
export type InspectionsReadPort = FactoryReadPort<InspectionTaskSummary>;
