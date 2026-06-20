export interface Filters {
  provinsi: string;
  lembaga: string;
  metode: string;
  riskMin: number;
}

export interface MetaResponse {
  total_rows: number;
  total_columns: number;
  columns: string[];
  source_file: string;
  source_kind: string;
  integrity: string;
  note: string;
}

export interface OverviewStats {
  total_paket: number;
  total_pagu_miliar: number;
  paket_kritis: number;
  avg_rpi: number;
  split_contract: number;
}

export interface FilterOptions {
  lembaga: string[];
  metode: string[];
  provinsi: string[];
}

export interface PaginatedPackages {
  data: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardBundle {
  overview: OverviewStats;
  signals: Record<string, number>;
  risk_distribution: { risk_label: string; count: number }[];
  metode: { metode: string; jumlah: number; avg_rpi: number }[];
  scatter: { pagu_miliar: number; RPI: number; risk_label: string }[];
  rank_lembaga: RankRow[];
  choropleth: ChoroplethRow[];
  rank_provinsi: RankRow[];
  kg: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] };
}

export interface ChoroplethRow {
  kabkot_id: string;
  kabkot_name: string;
  prov_name: string;
  n_paket: number;
  avg_rpi: number;
  total_pagu_miliar: number;
  n_kritis: number;
  n_tinggi: number;
}

export interface RankRow {
  lembaga?: string;
  prov_name?: string;
  avg_rpi: number;
  n_kritis: number;
  n_tinggi: number;
  n_paket: number;
}
