import axios from "axios";
import type {
  DashboardBundle,
  FilterOptions,
  Filters,
  MetaResponse,
  PaginatedPackages,
} from "../types";

/** Dev: Vite proxy `/api` → localhost:8000. Prod: set VITE_API_URL di Vercel. */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  timeout: 120_000,
});

async function withWarmupRetry<T>(fn: () => Promise<T>, attempts = 40): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (e) {
      lastError = e;
      if (axios.isAxiosError(e) && e.response?.status === 503) {
        await new Promise((r) => setTimeout(r, 3000));
        continue;
      }
      throw e;
    }
  }
  throw lastError;
}

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
  const { data } = await withWarmupRetry(() => api.get<MetaResponse>("/meta"));
  return data;
}

export async function fetchFilterOptions(): Promise<FilterOptions> {
  const { data } = await withWarmupRetry(() => api.get<FilterOptions>("/filters/options"));
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
  const { data } = await withWarmupRetry(() => api.get("/geo/kabkota"));
  return data;
}
