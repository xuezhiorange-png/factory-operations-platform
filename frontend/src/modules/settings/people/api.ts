import type { Factory } from '../../assets/contracts';
import type { Role } from '../../identity/account';
import { csrfHeaders } from '../../identity/account';
import { operationsApiPath } from '../../../shared/api-path';

export interface Person {
  id: string;
  display_name: string;
  role: Role | null;
  active: boolean;
  factories: Factory[];
  feishu_binding: 'bound' | 'unbound' | 'none';
  version: number;
}
export interface PageResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface AccessSnapshot {
  role: Role | null;
  active: boolean;
  factory_ids: string[];
  feishu_binding: Person['feishu_binding'];
  version: number;
}
export interface ChangeRecord {
  id: string;
  actor_id: string;
  action: string;
  occurred_at: string;
  details: { before: AccessSnapshot; after: AccessSnapshot; reason: string };
}
export interface MutationResult {
  user: Person;
  reauthentication_required: boolean;
}
export class PersonnelError extends Error {
  constructor(public readonly status: number) {
    super('Personnel request not confirmed');
  }
}
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;
const validRole = (value: unknown) =>
  value === null || ['group_lead', 'engineer', 'factory_equipment_admin'].includes(String(value));
const validFactory = (value: unknown) =>
  object(value) && ['id', 'code', 'name'].every((key) => typeof value[key] === 'string');
const validPerson = (value: unknown) =>
  object(value) &&
  typeof value.id === 'string' &&
  typeof value.display_name === 'string' &&
  validRole(value.role) &&
  typeof value.active === 'boolean' &&
  Number.isInteger(value.version) &&
  Number(value.version) > 0 &&
  ['bound', 'unbound', 'none'].includes(String(value.feishu_binding)) &&
  Array.isArray(value.factories) &&
  value.factories.every(validFactory);
const snapshot = (value: unknown) =>
  object(value) &&
  validRole(value.role) &&
  typeof value.active === 'boolean' &&
  Array.isArray(value.factory_ids) &&
  value.factory_ids.every((id) => typeof id === 'string') &&
  ['bound', 'unbound', 'none'].includes(String(value.feishu_binding));
const validRecord = (value: unknown) =>
  object(value) &&
  typeof value.id === 'string' &&
  typeof value.actor_id === 'string' &&
  typeof value.occurred_at === 'string' &&
  !Number.isNaN(Date.parse(value.occurred_at)) &&
  object(value.details) &&
  typeof value.details.reason === 'string' &&
  snapshot(value.details.before) &&
  snapshot(value.details.after);
async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const result = await fetch(operationsApiPath('/access' + url), {
    credentials: 'same-origin',
    cache: 'no-store',
    ...options,
  });
  if (!result.ok) throw new PersonnelError(result.status);
  try {
    const body: unknown = await result.json();
    if (!object(body)) throw new PersonnelError(502);
    if (options.method) {
      if (!validPerson(body.user) || typeof body.reauthentication_required !== 'boolean')
        throw new PersonnelError(502);
    } else if (
      !Array.isArray(body.items) ||
      !['total', 'limit', 'offset'].every(
        (key) => Number.isInteger(body[key]) && Number(body[key]) >= 0,
      ) ||
      !body.items.every(url.includes('/changes?') ? validRecord : validPerson)
    )
      throw new PersonnelError(502);
    return body as T;
  } catch {
    throw new PersonnelError(502);
  }
}
export const personnelApi = {
  list: (offset: number, signal?: AbortSignal) =>
    request<PageResult<Person>>(`/users?limit=20&offset=${offset}`, { signal }),
  history: (id: string, offset: number, signal?: AbortSignal) =>
    request<PageResult<ChangeRecord>>(
      `/users/${encodeURIComponent(id)}/changes?limit=20&offset=${offset}`,
      { signal },
    ),
  change: (
    id: string,
    body: {
      expected_version: number;
      reason: string;
      role: Role | null;
      active: boolean;
      factory_ids: string[];
    },
  ) =>
    request<MutationResult>(`/users/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: csrfHeaders(),
      body: JSON.stringify(body),
    }),
  lifecycle: (
    id: string,
    operation: 'revoke-sessions' | 'unbind-feishu',
    body: { expected_version: number; reason: string },
  ) =>
    request<MutationResult>(`/users/${encodeURIComponent(id)}/${operation}`, {
      method: 'POST',
      headers: csrfHeaders(),
      body: JSON.stringify(body),
    }),
};
