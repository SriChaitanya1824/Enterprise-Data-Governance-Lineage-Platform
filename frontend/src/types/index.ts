export type RecordData = { id: number; [key: string]: unknown };
export type Person = RecordData & { name: string; email: string; role: string };
export type Asset = RecordData & {
  name: string;
  description: string;
  domain: string;
  classification: string;
  criticality: string;
  source_system: string;
  owner: string | null;
  steward: string | null;
  quality_score: number | null;
  fields?: RecordData[];
  quality_results?: RecordData[];
  controls?: RecordData[];
  exceptions?: RecordData[];
  lineage?: GraphData;
};
export type GraphData = {
  nodes: Asset[];
  edges: (RecordData & {
    source_asset_id: number;
    target_asset_id: number;
    transformation: string;
    origin: string;
    source_field_id: number | null;
  })[];
  scope: string;
};
export type PageData<T = RecordData> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
export type Adoption = {
  domain: string;
  assets: number;
  adoption_score: number;
  ownership: number;
  metadata: number;
  lineage: number;
  quality: number;
  stewardship: number;
  classification: number;
  review: number;
  open_exceptions: number;
};
export type DashboardData = {
  total_assets: number;
  cdes: number;
  governed_assets: number;
  missing_ownership: number;
  missing_lineage: number;
  open_exceptions: number;
  overdue_exceptions: number;
  average_quality: number | null;
  adoption_score: number;
  adoption: Adoption[];
  exception_status: Record<string, number>;
  exception_severity: Record<string, number>;
  quality_results: Record<string, number>;
  assets_by_domain: Record<string, number>;
  lineage_completeness: Record<string, number>;
  quality_coverage: number;
};
