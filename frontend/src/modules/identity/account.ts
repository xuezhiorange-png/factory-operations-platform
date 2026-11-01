import { reactive, computed } from 'vue';
import type { Factory } from '../assets/contracts';

export type Role = 'group_lead' | 'engineer' | 'factory_equipment_admin';
export interface Account {
  id: string;
  display_name: string;
  role: Role | null;
  status: 'authorized' | 'pending';
  factories: Factory[];
}
type Status = 'loading' | 'anonymous' | 'expired' | 'error' | 'authorized' | 'pending';
export const roleNames: Record<Role, string> = {
  group_lead: '集团负责人',
  engineer: '工程师',
  factory_equipment_admin: '加工厂设备管理员',
};
export const account = reactive({
  status: 'loading' as Status,
  user: undefined as Account | undefined,
  configured: false,
  synthetic: false,
  selectedFactory: '',
});
export const accountLabel = computed(
  () =>
    account.user?.display_name ??
    {
      loading: '检查登录中',
      anonymous: '未登录',
      expired: '登录已过期',
      error: '身份服务异常',
      authorized: '',
      pending: '账号待授权',
    }[account.status],
);
let refreshGeneration = 0;

export async function refreshAccount() {
  const generation = ++refreshGeneration;
  account.status = 'loading';
  account.user = undefined;
  try {
    const config = await fetch('/api/v1/auth/config', {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    if (!config.ok) throw new Error('Unavailable');
    const capability = await config.json();
    if (generation !== refreshGeneration) return;
    account.configured = capability.configured === true;
    account.synthetic = capability.data_source === 'synthetic_test';
    const response = await fetch('/api/v1/auth/me', {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    if (response.status === 401) {
      const body = await response.json();
      if (generation !== refreshGeneration) return;
      account.status = body.error?.code === 'session_expired' ? 'expired' : 'anonymous';
      account.selectedFactory = '';
      return;
    }
    if (response.status === 503 && !account.configured) {
      account.status = 'anonymous';
      return;
    }
    if (!response.ok) throw new Error('Unavailable');
    const body = await response.json();
    if (generation !== refreshGeneration) return;
    if (
      !body ||
      typeof body.id !== 'string' ||
      typeof body.display_name !== 'string' ||
      !Array.isArray(body.factories) ||
      !['pending', 'authorized'].includes(body.status) ||
      (body.role !== null && !Object.keys(roleNames).includes(body.role))
    )
      throw new Error('Invalid response');
    account.user = body as Account;
    account.status = body.status;
    if (!body.factories.some((factory: Factory) => factory.id === account.selectedFactory))
      account.selectedFactory = body.factories[0]?.id ?? '';
  } catch {
    if (generation !== refreshGeneration) return;
    account.status = 'error';
    account.user = undefined;
    account.selectedFactory = '';
  }
}

export function csrfHeaders(): Record<string, string> {
  const nonce =
    document.cookie
      .split('; ')
      .find((item) => item.startsWith('__Host-factory_ops_csrf='))
      ?.split('=')[1] ?? '';
  return { 'Content-Type': 'application/json', 'X-CSRF-Token': nonce };
}

export async function startLogin(returnTo: string, channel: 'pc' | 'h5') {
  const response = await fetch('/api/v1/auth/feishu/start', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ return_to: returnTo, channel }),
  });
  if (!response.ok) throw new Error('Login unavailable');
  const body = await response.json();
  const destination = new URL(body.authorization_url);
  if (
    destination.origin !== 'https://accounts.feishu.cn' ||
    destination.pathname !== '/open-apis/authen/v1/authorize'
  )
    throw new Error('Invalid destination');
  window.location.assign(destination.href);
}

export async function logout() {
  const response = await fetch('/api/v1/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: csrfHeaders(),
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('Logout failed');
  refreshGeneration++;
  account.user = undefined;
  account.status = 'anonymous';
  account.selectedFactory = '';
}

export function loginTarget(path: string) {
  return path.startsWith('/m/') ? '/m/login' : '/login';
}
export function internalTarget(value: unknown, fallback: string) {
  return typeof value === 'string' &&
    /^\/(?:m\/)?(?:workbench|home|tasks|scan|messages|me|assets|settings|inspections|issues|work-orders|maintenance|inventory|analytics)(?:[/?][A-Za-z0-9_?=&/.-]*)?$/.test(
      value,
    )
    ? value
    : fallback;
}
