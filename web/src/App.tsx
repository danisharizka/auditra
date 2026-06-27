import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchDashboardBundle,
  fetchFilterOptions,
  fetchGeoJson,
  fetchMeta,
  fetchPackages,
} from "./api/client";
import { formatApiError } from "./api/errors";
import ColorLegend from "./components/ColorLegend";
import ChoroplethMap from "./components/ChoroplethMap";
import { MetodeBar, RadarChart, RiskDonut, ScatterChart } from "./components/Charts";
import EntitySidebar from "./components/EntitySidebar";
import FilterBar from "./components/FilterBar";
import KgNetwork from "./components/KgNetwork";
import PackagesTable from "./components/PackagesTable";
import { RankProvinsi } from "./components/RankLists";
import AppHeader from "./components/AppHeader";
import Logo from "./components/Logo";
import SiteFooter from "./components/SiteFooter";
import StatCards from "./components/StatCards";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import { useTheme } from "./theme/ThemeContext";
import type {
  ChoroplethRow,
  FilterOptions,
  Filters,
  GeoCoverage,
  MapOwnerMode,
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
  const { toggle, isDark } = useTheme();
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [options, setOptions] = useState<FilterOptions>({
    lembaga: [],
    metode: [],
    provinsi: [],
  });
  const [error, setError] = useState<string | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [packagesLoading, setPackagesLoading] = useState(false);

  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [geoCoverage, setGeoCoverage] = useState<GeoCoverage | null>(null);
  const [choroplethModes, setChoroplethModes] = useState<Record<MapOwnerMode, ChoroplethRow[]>>({
    kl: [],
    pemprov: [],
    pemkot: [],
    others: [],
  });
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

  const onLembagaSelect = useCallback(
    (lembaga: string) => {
      onFilterChange({
        lembaga: filters.lembaga === lembaga ? "ALL" : lembaga,
      });
    },
    [filters.lembaga, onFilterChange]
  );

  const onRegionClick = useCallback(
    (provinsi: string) => {
      onFilterChange({
        provinsi: filters.provinsi === provinsi ? "ALL" : provinsi,
      });
    },
    [filters.provinsi, onFilterChange]
  );

  useEffect(() => {
    (async () => {
      try {
        const [, opt, geo] = await Promise.all([
          fetchMeta(),
          fetchFilterOptions(),
          fetchGeoJson(),
        ]);
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
    setDashboardError(null);
    (async () => {
      try {
        const bundle = await fetchDashboardBundle(debouncedFilters);
        if (gen !== dashboardGen.current) return;
        setOverview(bundle.overview);
        setGeoCoverage(bundle.geo_coverage);
        setChoroplethModes(
          bundle.choropleth_modes ?? {
            kl: bundle.choropleth,
            pemprov: [],
            pemkot: [],
            others: [],
          }
        );
        setRiskDist(bundle.risk_distribution);
        setMetode(bundle.metode);
        setScatter(bundle.scatter);
        setSignals(bundle.signals);
        setRankLembaga(bundle.rank_lembaga);
        setRankProvinsi(bundle.rank_provinsi);
        setKg(bundle.kg);
        setDashboardError(null);
      } catch (e) {
        console.error(e);
        if (gen === dashboardGen.current) {
          setDashboardError(formatApiError(e));
        }
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
      <div className="app-shell flex min-h-screen flex-col items-center justify-center gap-6 p-6 sm:p-8">
        <Logo size="lg" />
        <div className="panel max-w-lg border-red-400 dark:border-red-800">
          <h1 className="text-lg font-bold text-red-600 dark:text-red-400">Dataset belum siap</h1>
          <p className="mt-2 whitespace-pre-line text-sm text-muted">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell pb-10">
      <div className="mx-auto max-w-[1500px] px-3 sm:px-4">
        <AppHeader isDark={isDark} onToggleTheme={toggle} />

        <FilterBar filters={filters} onChange={onFilterChange} options={options} />

        {loading && (
          <p className="mb-2 text-xs font-medium" style={{ color: "var(--accent-loading)" }}>
            Memperbarui dari seluruh dataset…
          </p>
        )}

        {dashboardError && (
          <p className="mb-2 rounded-lg border border-red-400/50 bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">
            Gagal memuat data filter: {dashboardError}
          </p>
        )}

        <StatCards stats={overview} geoCoverage={geoCoverage} />

        <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="panel lg:col-span-8">
            <h2 className="mb-1 text-sm font-semibold text-primary">Peta Prioritas Audit per Kab/Kota</h2>
            <p className="mb-3 text-xs text-muted">
              Mode pemilik paket (K/L · Pemprov · Pemkot · Lainnya) · peta seluruh Indonesia
            </p>
            <ChoroplethMap
              modes={choroplethModes}
              geojson={geojson}
              isDark={isDark}
              onRegionClick={onRegionClick}
            />
          </div>
          <div className="panel lg:col-span-4 lg:self-start">
            <h2 className="mb-1 text-sm font-semibold text-primary">Lembaga Prioritas Audit</h2>
            <p className="mb-2 text-[10px] text-muted">
              Top {8} default · klik untuk filter · Eks = KRITIS + anomali pagu/fragmentasi
            </p>
            <EntitySidebar
              data={rankLembaga}
              selectedLembaga={filters.lembaga !== "ALL" ? filters.lembaga : undefined}
              onSelect={onLembagaSelect}
            />
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-12">
          <div className="panel lg:col-span-4">
            <h2 className="mb-2 text-sm font-semibold text-primary">Distribusi Risiko</h2>
            <RiskDonut data={riskDist} />
          </div>
          <div className="panel lg:col-span-4">
            <h2 className="mb-2 text-sm font-semibold text-primary">Profil 7 Sinyal RPI</h2>
            <RadarChart signals={signals} />
          </div>
          <div className="panel max-h-[360px] overflow-y-auto lg:col-span-4">
            <h2 className="mb-3 text-sm font-semibold text-primary">Provinsi Paling Berisiko</h2>
            <RankProvinsi data={rankProvinsi} />
          </div>
        </div>

        <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-12">
          <div className="panel lg:col-span-5">
            <h2 className="mb-2 text-sm font-semibold text-primary">Rata-rata RPI per Metode</h2>
            <MetodeBar data={metode} />
            <ColorLegend
              className="mt-2"
              items={[
                { color: "#3b82f6", label: "Biru — RPI < 30" },
                { color: "#f97316", label: "Oranye — RPI ≥ 30" },
              ]}
            />
          </div>
          <div className="panel lg:col-span-7">
            <h2 className="mb-2 text-sm font-semibold text-primary">Distribusi Pagu vs RPI</h2>
            <p className="mb-2 text-[11px] text-muted">
              Scatter max 3.000 titik · Biru = rendah, oranye/merah = tinggi risiko
            </p>
            <ScatterChart points={scatter} />
          </div>
        </div>

        <div className="panel mb-4">
          <h2 className="mb-1 text-sm font-semibold text-primary">Knowledge Graph Lembaga & Satker</h2>
          <p className="mb-3 text-xs text-muted">
            Subgraf lembaga–satker mengikuti filter aktif · kesimpulan diperbarui otomatis
          </p>
          <KgNetwork
            key={`${debouncedFilters.provinsi}|${debouncedFilters.lembaga}|${debouncedFilters.metode}|${debouncedFilters.riskMin}`}
            nodes={kg.nodes}
            edges={kg.edges}
          />
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

        <SiteFooter />
      </div>
    </div>
  );
}
