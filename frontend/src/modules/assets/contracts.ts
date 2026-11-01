/** Real M1-01 read contracts. No identity, attachment or mutation fields. */
export type AssetCategory = 'refrigeration' | 'processing' | 'utilities' | 'other';
export type AssetStatus = 'pending' | 'in_use' | 'inactive' | 'retired';
export type DataSource = 'configured_database' | 'synthetic_test';
export interface Factory {
  id: string;
  code: string;
  name: string;
}
export interface Asset {
  id: string;
  factory_id: string;
  asset_code: string;
  name: string;
  category: AssetCategory;
  status: AssetStatus;
  location: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}
export interface FactoryList {
  items: Factory[];
  data_source: DataSource;
}
export interface AssetList {
  items: Asset[];
  total: number;
  limit: number;
  offset: number;
  data_source: DataSource;
}
export interface AssetDetail {
  asset: Asset;
  data_source: DataSource;
}
export interface AssetQuery {
  q?: string;
  category?: AssetCategory;
  status?: AssetStatus;
  limit?: number;
  offset?: number;
}
export interface AssetsReadPort {
  factories(signal?: AbortSignal): Promise<FactoryList>;
  search(factoryId: string, query: AssetQuery, signal?: AbortSignal): Promise<AssetList>;
  detail(factoryId: string, assetId: string, signal?: AbortSignal): Promise<AssetDetail>;
}
