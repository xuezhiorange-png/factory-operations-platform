/** Future API boundaries only. No adapter, business request or mock implementation in M0.5. */
export interface FactoryScope {
  factoryId: string;
}
export interface ListQuery {
  search?: string;
  cursor?: string;
  limit?: number;
}
export interface PageResult<T> {
  items: readonly T[];
  nextCursor?: string;
}
export interface FactoryReadPort<T> {
  list(scope: FactoryScope, query: ListQuery): Promise<PageResult<T>>;
  get(scope: FactoryScope, id: string): Promise<T>;
}
export type IntegrationState = 'not-connected';
// A UI route/factory context never substitutes for server-side authorization.
