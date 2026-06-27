import { useMemo, useState } from "react";
import ColorLegend from "./ColorLegend";
import Plot from "react-plotly.js";
import type { PlotMouseEvent } from "plotly.js";
import { useTheme } from "../theme/ThemeContext";
import type { ChoroplethRow, MapOwnerMode } from "../types";
import { formatPaguCompact } from "../utils/formatPagu";
import { normalizeKabkotId } from "../utils/kabkotId";

export type MapMetric = "rpi" | "pagu_risiko";

const MODE_OPTIONS: { id: MapOwnerMode; label: string }[] = [
  { id: "kl", label: "Kementerian/Lembaga" },
  { id: "pemprov", label: "Pemprov" },
  { id: "pemkot", label: "Pemkot/Kab" },
  { id: "others", label: "Lainnya" },
];

const MODE_LEGEND_TITLE: Record<MapOwnerMode, string> = {
  kl: "Prioritas audit paket K/L per kab/kota",
  pemprov: "Prioritas audit paket pemprov per kab/kota",
  pemkot: "Prioritas audit paket pemkot/kab per kab/kota",
  others: "Prioritas audit paket lainnya per kab/kota",
};

/** Warna lebih kontras — mirip referensi AUD (biru → kuning → oranye → merah). */
const COLORSCALE_DARK: [number, string][] = [
  [0, "#1e293b"],
  [0.08, "#2563eb"],
  [0.28, "#60a5fa"],
  [0.48, "#fbbf24"],
  [0.68, "#f97316"],
  [0.88, "#ef4444"],
  [1, "#b91c1c"],
];

const COLORSCALE_LIGHT: [number, string][] = [
  [0, "#e2e8f0"],
  [0.08, "#93c5fd"],
  [0.28, "#fde047"],
  [0.48, "#fb923c"],
  [0.68, "#f97316"],
  [0.88, "#ef4444"],
  [1, "#991b1b"],
];

const INDONESIA_GEO = {
  lonaxis: { range: [94, 142] as [number, number] },
  lataxis: { range: [-12, 7] as [number, number] },
};

interface Props {
  modes: Record<MapOwnerMode, ChoroplethRow[]>;
  geojson: GeoJSON.FeatureCollection | null;
  isDark?: boolean;
  onRegionClick?: (provinsi: string, kabkotName: string) => void;
}

function quantileLabels(values: number[], isDark: boolean): { color: string; label: string }[] {
  const positive = values.filter((v) => v > 0);
  if (positive.length === 0) {
    return [{ color: isDark ? "#1e293b" : "#e2e8f0", label: "Tidak ada data" }];
  }
  const sorted = [...positive].sort((a, b) => a - b);
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1)))];

  const breaks = [0, q(0.2), q(0.4), q(0.6), q(0.8), q(1)];
  const palette = isDark ? COLORSCALE_DARK : COLORSCALE_LIGHT;

  const items = [{ color: palette[0][1], label: "Tidak ada / nol" }];
  for (let i = 0; i < 5; i++) {
    const lo = breaks[i];
    const hi = breaks[i + 1];
    const color = palette[Math.min(i + 2, palette.length - 1)][1];
    const label =
      i === 0 && lo === hi
        ? formatPaguCompact(lo)
        : `${formatPaguCompact(Math.max(lo, 0.0001))} – ${formatPaguCompact(hi)}`;
    items.push({ color, label });
  }
  return items;
}

export default function ChoroplethMap({ modes, geojson, isDark: isDarkProp, onRegionClick }: Props) {
  const { colors, isDark: isDarkTheme } = useTheme();
  const isDark = isDarkProp ?? isDarkTheme;
  const [ownerMode, setOwnerMode] = useState<MapOwnerMode>("kl");
  const [metric, setMetric] = useState<MapMetric>("pagu_risiko");

  const data = modes[ownerMode] ?? [];

  const normalizedGeo = useMemo(() => {
    if (!geojson) return null;
    return {
      ...geojson,
      features: geojson.features.map((f) => ({
        ...f,
        properties: {
          ...f.properties,
          kabkot_id: normalizeKabkotId(f.properties?.kabkot_id as string | number),
        },
      })),
    };
  }, [geojson]);

  const plotConfig = useMemo(() => {
    if (!normalizedGeo) return null;

    const dataById = new Map(
      data.map((d) => [normalizeKabkotId(d.kabkot_id), d] as const)
    );

    const locations = normalizedGeo.features.map(
      (f) => f.properties?.kabkot_id as string
    );
    const isPagu = metric === "pagu_risiko";
    const z = locations.map((id) => {
      const row = dataById.get(id);
      return isPagu ? (row?.pagu_risiko_miliar ?? 0) : (row?.avg_rpi ?? 0);
    });
    const text = locations.map((id) => {
      const row = dataById.get(id);
      if (!row) return `${id}<br>Tidak ada paket (mode ini)`;
      const paguLine = `Pagu berisiko: ${formatPaguCompact(row.pagu_risiko_miliar ?? 0)}`;
      return `${row.kabkot_name}<br>${row.prov_name}<br>Paket: ${row.n_paket}<br>Avg RPI: ${row.avg_rpi}<br>${paguLine}<br>Kritis: ${row.n_kritis}`;
    });

    const colorscale = isDark ? COLORSCALE_DARK : COLORSCALE_LIGHT;
    const positiveZ = z.filter((v) => v > 0);
    const zmax = isPagu
      ? Math.max(...positiveZ, 0.01)
      : Math.max(60, ...positiveZ, 1);

    return {
      data: [
        {
          type: "choropleth" as const,
          geojson: normalizedGeo,
          locations,
          z,
          text,
          featureidkey: "properties.kabkot_id",
          colorscale,
          zmin: 0,
          zmax,
          marker: { line: { width: 0.35, color: isDark ? "#475569" : "#94a3b8" } },
          hovertemplate: "%{text}<extra></extra>",
          colorbar: {
            tickfont: { color: colors.textPrimary },
            title: {
              text: isPagu ? "Pagu Berisiko (Miliar Rp)" : "Avg RPI",
              font: { color: colors.textPrimary, size: 11 },
            },
          },
        },
      ],
      layout: {
        geo: {
          ...INDONESIA_GEO,
          bgcolor: colors.chartBg,
          showframe: false,
          showcoastlines: true,
          coastlinecolor: isDark ? "#475569" : "#94a3b8",
          showland: true,
          landcolor: isDark ? "#0f172a" : "#f1f5f9",
          showocean: true,
          oceancolor: colors.chartBg,
          lakecolor: colors.chartBg,
          projection: { type: "mercator" as const },
        },
        paper_bgcolor: colors.chartBg,
        plot_bgcolor: colors.chartBg,
        margin: { t: 0, b: 0, l: 0, r: 0 },
        height: 480,
        font: { color: colors.textPrimary, family: "Inter, system-ui" },
      },
    };
  }, [normalizedGeo, data, isDark, colors.textPrimary, colors.chartBg, metric]);

  const paguValues = useMemo(
    () => data.map((d) => d.pagu_risiko_miliar ?? 0).filter((v) => v > 0),
    [data]
  );

  const handleClick = (ev: Readonly<PlotMouseEvent>) => {
    if (!onRegionClick) return;
    const pt = ev.points?.[0];
    if (!pt || !("location" in pt)) return;
    const loc = normalizeKabkotId(String(pt.location));
    const row = data.find((d) => normalizeKabkotId(d.kabkot_id) === loc);
    if (row?.prov_name) onRegionClick(row.prov_name, row.kabkot_name);
  };

  if (!geojson) {
    return <div className="flex h-[480px] items-center justify-center text-muted">Memuat peta…</div>;
  }

  if (!plotConfig) {
    return <div className="flex h-[480px] items-center justify-center text-muted">Memuat peta…</div>;
  }

  const legendItems =
    metric === "pagu_risiko"
      ? quantileLabels(paguValues, isDark)
      : [
          { color: isDark ? "#1e293b" : "#e2e8f0", label: "Tidak ada / RPI ≈ 0" },
          { color: isDark ? "#60a5fa" : "#93c5fd", label: "Rendah" },
          { color: isDark ? "#fbbf24" : "#fde047", label: "Sedang" },
          { color: isDark ? "#f97316" : "#fb923c", label: "Tinggi" },
          { color: "#ef4444", label: "Sangat tinggi (RPI ≥ 50)" },
        ];

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {MODE_OPTIONS.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`tab-btn ${ownerMode === m.id ? "tab-btn-active" : ""}`}
            onClick={() => setOwnerMode(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={`tab-btn ${metric === "pagu_risiko" ? "tab-btn-active" : ""}`}
          onClick={() => setMetric("pagu_risiko")}
        >
          Pagu Berisiko
        </button>
        <button
          type="button"
          className={`tab-btn ${metric === "rpi" ? "tab-btn-active" : ""}`}
          onClick={() => setMetric("rpi")}
        >
          Prioritas RPI
        </button>
      </div>

      <Plot
        data={plotConfig.data}
        layout={plotConfig.layout}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%", height: 480, background: colors.chartBg }}
        onClick={handleClick}
      />

      <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
        {MODE_LEGEND_TITLE[ownerMode]}
      </p>
      <ColorLegend className="mt-1 justify-center sm:justify-start" items={legendItems} />
      <p className="mt-2 text-[10px] text-muted">
        Peta seluruh Indonesia · Wilayah tanpa warna = tidak ada paket pada mode ini · Klik wilayah
        untuk filter provinsi · Multi-lokasi dihitung penuh per kab/kota.
      </p>
    </div>
  );
}
