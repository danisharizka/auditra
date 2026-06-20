import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchDashboardBundle,
  fetchFilterOptions,
  fetchGeoJson,
  fetchMeta,
  fetchPackages,
} from "./api/client";
import { formatApiError } from "./api/errors";
import ChoroplethMap from "./components/ChoroplethMap";
import { MetodeBar, RadarChart, RiskDonut, ScatterChart } from "./components/Charts";
import FilterBar from "./components/FilterBar";
import KgNetwork from "./components/KgNetwork";
import PackagesTable from "./components/PackagesTable";
import { RankLembaga, RankProvinsi } from "./components/RankLists";
import StatCards from "./components/StatCards";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import { useTheme } from "./theme/ThemeContext";
import type {
  ChoroplethRow,
  FilterOptions,
  Filters,
  MetaResponse,
  OverviewStats,
  PaginatedPackages,
  RankRow,
} from "./types";

const defaultFilters: Filters = {
  provinsi: "ALL",
  lembaga: "ALL",
  metode: "ALL",
  riskMin: 0,
};

export default function App() {
  const { toggle, isDark, mode } = useTheme();
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [options, setOptions] = useState<FilterOptions>({
    lembaga: [],
    metode: [],
    provinsi: [],
  });
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [packagesLoading, setPackagesLoading] = useState(false);

  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [choropleth, setChoropleth] = useState<ChoroplethRow[]>([]);
  const [geojson, setGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [riskDist, setRiskDist] = useState<{ risk_label: string; count: number }[]>([]);
  const [metode, setMetode] = useState<{ metode: string; jumlah: number; avg_rpi: number }[]>([]);
  const [scatter, setScatter] = useState<{ pagu_miliar: number; RPI: number; risk_label: string }[]>(
    []
  );
  const [signals, setSignals] = useState<Record<string, number>>({});
  const [rankLembaga, setRankLembaga] = useState<RankRow[]>([]);
  const [rankProvinsi, setRankProvinsi] = useState<RankRow[]>([]);
  const [kg, setKg] = useState<{ nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }>(
    { nodes: [], edges: [] }
  );
  const [packages, setPackages] = useState<PaginatedPackages | null>(null);
  const [page, setPage] = useState(1);

  const debouncedFilters = useDebouncedValue(filters, 350);
  const dashboardGen = useRef(0);
  const packagesGen = useRef(0);

  const onFilterChange = useCallback((next: Partial<Filters>) => {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [m, opt, geo] = await Promise.all([
          fetchMeta(),
          fetchFilterOptions(),
          fetchGeoJson(),
        ]);
        setMeta(m);
        setOptions(opt);
        setGeojson(geo as GeoJSON.FeatureCollection);
        setError(null);
      } catch (e: unknown) {
        setError(formatApiError(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (error) return;
    const gen = ++dashboardGen.current;
    setLoading(true);
    (async () => {
      try {
        const bundle = await fetchDashboardBundle(debouncedFilters);
        if (gen !== dashboardGen.current) return;
        setOverview(bundle.overview);
        setChoropleth(bundle.choropleth);
        setRiskDist(bundle.risk_distribution);
        setMetode(bundle.metode);
        setScatter(bundle.scatter);
        setSignals(bundle.signals);
        setRankLembaga(bundle.rank_lembaga);
        setRankProvinsi(bundle.rank_provinsi);
        setKg(bundle.kg);
      } catch (e) {
        console.error(e);
      } finally {
        if (gen === dashboardGen.current) setLoading(false);
      }
    })();
  }, [debouncedFilters, error]);

  useEffect(() => {
    if (error) return;
    const gen = ++packagesGen.current;
    setPackagesLoading(true);
    (async () => {
      try {
        const pkg = await fetchPackages(debouncedFilters, page, 50);
        if (gen !== packagesGen.current) return;
        setPackages(pkg);
      } catch (e) {
        console.error(e);
      } finally {
        if (gen === packagesGen.current) setPackagesLoading(false);
      }
    })();
  }, [debouncedFilters, page, error]);

  if (error) {
    return (
      <div className="app-shell flex min-h-screen items-center justify-center p-8">
        <div className="panel max-w-lg border-red-400 dark:border-red-800">
          <h1 className="text-lg font-bold text-red-600 dark:text-red-400">Dataset belum siap</h1>
          <p className="mt-2 whitespace-pre-line text-sm text-muted">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell pb-10">
      <div className="mx-auto max-w-[1500px] px-4">
        <header className="flex items-center justify-between py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-orange-500 text-sm font-extrabold text-white">
              AD
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-primary">Auditra</h1>
              <p className="text-xs text-muted">
                Sistem Prioritas Audit Pengadaan Publik — Knowledge Graph & Analisis Jaringan
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-right text-xs">
            <button
              type="button"
              onClick={toggle}
              className="btn-secondary flex items-center gap-1.5 text-xs"
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? "☀ Light" : "🌙 Dark"}
            </button>
            <div>
              <span className="font-semibold" style={{ color: "var(--accent-live)" }}>
                ● LIVE
              </span>
              <span className="badge-pill ml-3">TA 2026</span>
              {meta && (
                <p className="mt-1 text-muted">
                  Dataset: {meta.total_rows.toLocaleString("id-ID")} baris × {meta.total_columns} kolom
                  ({meta.integrity})
                </p>
              )}
            </div>
          </div>
        </header>

        <FilterBar filters={filters} onChange={onFilterChange} options={options} />

        {loading && (
          <p className="mb-2 text-xs font-medium" style={{ color: "var(--accent-loading)" }}>
            Memperbarui dari seluruh dataset…
          </p>
        )}

        <StatCards stats={overview} />

        <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="panel lg:col-span-8">
            <h2 className="mb-1 text-sm font-semibold text-primary">Peta Risiko Pengadaan per Kabupaten/Kota</h2>
            <p className="mb-3 text-xs text-muted">
              Agregat dihitung dari seluruh paket yang match filter — bukan sample
            </p>
            <ChoroplethMap data={choropleth} geojson={geojson} isDark={isDark} />
          </div>
          <div className="space-y-4 lg:col-span-4">
            <div className="panel">
              <h2 className="mb-2 text-sm font-semibold text-primary">Distribusi Risiko</h2>
              <RiskDonut data={riskDist} />
            </div>
            <div className="panel">
              <h2 className="mb-2 text-sm font-semibold text-primary">Profil Sinyal Risiko</h2>
              <RadarChart signals={signals} />
            </div>
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="panel lg:col-span-5">
            <h2 className="mb-2 text-sm font-semibold text-primary">Rata-rata RPI per Metode</h2>
            <MetodeBar data={metode} />
          </div>
          <div className="panel lg:col-span-7">
            <h2 className="mb-2 text-sm font-semibold text-primary">Distribusi Pagu vs RPI</h2>
            <p className="mb-2 text-[11px] text-muted">
              Scatter max 3.000 titik untuk performa; statistik card/table pakai semua baris
            </p>
            <ScatterChart points={scatter} />
          </div>
        </div>

        <div className="panel mb-4">
          <h2 className="mb-1 text-sm font-semibold text-primary">Knowledge Graph — Jaringan Lembaga & Satker</h2>
          <p className="mb-3 text-xs text-muted">Oranye: RPI ≥ 30 · Biru: RPI &lt; 30</p>
          <KgNetwork nodes={kg.nodes} edges={kg.edges} />
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="panel max-h-[480px] overflow-y-auto">
            <h2 className="mb-3 text-sm font-semibold text-primary">Lembaga Paling Berisiko</h2>
            <RankLembaga data={rankLembaga} />
          </div>
          <div className="panel max-h-[480px] overflow-y-auto">
            <h2 className="mb-3 text-sm font-semibold text-primary">Provinsi Paling Berisiko</h2>
            <RankProvinsi data={rankProvinsi} />
          </div>
        </div>

        <div className="panel">
          <h2 className="mb-3 text-sm font-semibold text-primary">Daftar Paket Prioritas Audit</h2>
          <PackagesTable
            result={packages}
            page={page}
            loading={packagesLoading}
            onPage={setPage}
          />
        </div>

        <p className="mt-6 text-center text-[11px] text-muted">
          Auditra © 2026 — Data: SIRUP LKPP · Mode: {mode} · Metode: Knowledge Graph + Rule-based Scoring
        </p>
      </div>
    </div>
  );
}
