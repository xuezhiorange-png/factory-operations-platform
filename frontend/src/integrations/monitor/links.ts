import { operationsApiPath } from '../../shared/api-path';
export interface MonitorLink {
  factory_id: string;
  asset_id: string;
  monitor_factory_id: string;
  monitor_gateway_id: string;
  monitor_device_id: string;
  valid_from: string;
  valid_to: string | null;
}
export async function readLink(kind: 'asset-link' | 'resolve', query: Record<string, string>, signal: AbortSignal) {
  const response = await fetch(operationsApiPath(`/portal/${kind}?${new URLSearchParams(query)}`), {
    credentials: 'same-origin', cache: 'no-store', signal,
  });
  if (!response.ok) throw new Error(`关联查询未确认（${response.status}）`);
  const body = await response.json();
  if (body?.status === 'unlinked' && body.link === null) return null;
  const link = body?.link;
  if (body?.status !== 'linked' || !link ||
    !['factory_id', 'asset_id', 'monitor_factory_id', 'monitor_gateway_id', 'monitor_device_id', 'valid_from'].every(key => typeof link[key] === 'string') ||
    (kind === 'asset-link' && (link.factory_id !== query.factory_id || link.asset_id !== query.asset_id)) ||
    (kind === 'resolve' && (link.monitor_factory_id !== query.monitor_factory_id || link.monitor_device_id !== query.monitor_device_id)))
    throw new Error('关联响应无效');
  return link as MonitorLink;
}
