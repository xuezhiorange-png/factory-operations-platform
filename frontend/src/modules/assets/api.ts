import type {
  Asset,
  AssetDetail,
  AssetList,
  AssetQuery,
  AssetsReadPort,
  FactoryList,
} from './contracts';

export class AssetApiError extends Error {
  constructor(public readonly status: number) {
    super('Asset read request failed');
  }
}
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;
const dataSource = (value: unknown) =>
  value === 'configured_database' || value === 'synthetic_test';
const asset = (value: unknown): value is Asset =>
  object(value) &&
  [
    'id',
    'factory_id',
    'asset_code',
    'name',
    'category',
    'status',
    'created_at',
    'updated_at',
  ].every((key) => typeof value[key] === 'string') &&
  ['location', 'manufacturer', 'model', 'serial_number'].every(
    (key) => value[key] === null || typeof value[key] === 'string',
  ) &&
  ['refrigeration', 'processing', 'utilities', 'other'].includes(String(value.category)) &&
  ['pending', 'in_use', 'inactive', 'retired'].includes(String(value.status)) &&
  typeof value.version === 'number';
async function read(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(path, { credentials: 'same-origin', cache: 'no-store', signal });
  if (!response.ok) throw new AssetApiError(response.status);
  try {
    return (await response.json()) as unknown;
  } catch {
    throw new AssetApiError(502);
  }
}
const factoryPath = (factoryId: string) =>
  '/api/v1/factories/' + encodeURIComponent(factoryId) + '/assets';
export const assetsApi: AssetsReadPort = {
  async factories(signal) {
    const body = await read('/api/v1/factories', signal);
    if (
      !object(body) ||
      !dataSource(body.data_source) ||
      !Array.isArray(body.items) ||
      !body.items.every(
        (item) =>
          object(item) && ['id', 'code', 'name'].every((key) => typeof item[key] === 'string'),
      )
    )
      throw new AssetApiError(502);
    return body as unknown as FactoryList;
  },
  async search(factoryId: string, query: AssetQuery, signal) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query))
      if (value !== undefined && value !== '') params.set(key, String(value));
    const body = await read(factoryPath(factoryId) + '?' + params.toString(), signal);
    if (
      !object(body) ||
      !dataSource(body.data_source) ||
      !Array.isArray(body.items) ||
      !body.items.every((item) => asset(item) && item.factory_id === factoryId) ||
      !['total', 'limit', 'offset'].every((key) => typeof body[key] === 'number')
    )
      throw new AssetApiError(502);
    return body as unknown as AssetList;
  },
  async detail(factoryId, assetId, signal) {
    const body = await read(factoryPath(factoryId) + '/' + encodeURIComponent(assetId), signal);
    if (
      !object(body) ||
      !dataSource(body.data_source) ||
      !asset(body.asset) ||
      body.asset.factory_id !== factoryId ||
      body.asset.id !== assetId
    )
      throw new AssetApiError(502);
    return body as unknown as AssetDetail;
  },
};
