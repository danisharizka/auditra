import axios from "axios";
import type {
  ChoroplethRow,
  DashboardBundle,
  FilterOptions,
  Filters,
  MetaResponse,
  OverviewStats,
  PaginatedPackages,
  RankRow,
} from "../types";

/** Dev: Vite proxy `/api` → localhost:8000. Prod: set VITE_API_URL di Vercel. */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
});

function params(f: Filters, extra: Record<string, unknown> = {}) {
  return {
    provinsi: f.provinsi,
    lembaga: f.lembaga,
    metode: f.metode,
    risk_min: f.riskMin,
    ...extra,
  };
}

export async function fetchMeta(): Promise<MetaResponse> {
  const { data } = await api.get<MetaResponse>("/meta");
  return data;
}

export async function fetchFilterOptions(): Promise<FilterOptions> {
  const { data } = await api.get<FilterOptions>("/filters/options");
  return data;
}

/** All chart data in ONE request (fast, cached server-side). */
export async function fetchDashboardBundle(f: Filters): Promise<DashboardBundle> {
  const { data } = await api.get<DashboardBundle>("/dashboard/bundle", { params: params(f) });
  return data;
}

export async function fetchPackages(
  f: Filters,
  page: number,
  pageSize: number
): Promise<PaginatedPackages> {
  const { data } = await api.get<PaginatedPackages>("/packages", {
    params: {
      ...params(f),
      risk_min: Math.max(f.riskMin, 30),
      page,
      page_size: pageSize,
    },
  });
  return data;
}

export async function fetchGeoJson() {
  const { data } = await api.get("/geo/kabkota");
  return data;
}

// Legacy individual endpoints (kept for compatibility / docs)
export async function fetchOverview(f: Filters): Promise<OverviewStats> {
  const { data } = await api.get<OverviewStats>("/overview", { params: params(f) });
  return data;
}

export async function fetchChoropleth(f: Filters): Promise<ChoroplethRow[]> {
  const { data } = await api.get<ChoroplethRow[]>("/charts/choropleth", {
    params: { lembaga: f.lembaga, metode: f.metode, risk_min: f.riskMin },
  });
  return data;
}

export async function fetchRiskDistribution(f: Filters) {
  const { data } = await api.get("/charts/risk-distribution", { params: params(f) });
  return data as { risk_label: string; count: number }[];
}

export async function fetchMetode(f: Filters) {
  const { data } = await api.get("/charts/metode", { params: params(f) });
  return data as { metode: string; jumlah: number; avg_rpi: number }[];
}

export async function fetchScatter(f: Filters) {
  const { data } = await api.get("/charts/scatter", { params: params(f) });
  return data as { points: Record<string, unknown>[]; note: string };
}

export async function fetchSignals(f: Filters) {
  const { data } = await api.get<Record<string, number>>("/charts/signals", {
    params: params(f),
  });
  return data;
}

export async function fetchRankLembaga(f: Filters): Promise<RankRow[]> {
  const { data } = await api.get<RankRow[]>("/rankings/lembaga", { params: params(f) });
  return data;
}

export async function fetchRankProvinsi(f: Filters): Promise<RankRow[]> {
  const { data } = await api.get<RankRow[]>("/rankings/provinsi", {
    params: { lembaga: f.lembaga, metode: f.metode, risk_min: f.riskMin },
  });
  return data;
}

export async function fetchKg(lembaga: string) {
  const { data } = await api.get("/kg", { params: { lembaga } });
  return data as { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] };
}