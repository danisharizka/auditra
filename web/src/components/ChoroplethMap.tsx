import { useMemo } from "react";
import ColorLegend from "./ColorLegend";
import Plot from "react-plotly.js";
import { useTheme } from "../theme/ThemeContext";
import type { ChoroplethRow } from "../types";
import { normalizeKabkotId } from "../utils/kabkotId";

interface Props {
  data: ChoroplethRow[];
  geojson: GeoJSON.FeatureCollection | null;
  isDark?: boolean;
}

export default function ChoroplethMap({ data, geojson, isDark: isDarkProp }: Props) {
  const { colors, isDark: isDarkTheme } = useTheme();
  const isDark = isDarkProp ?? isDarkTheme;

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
    if (!normalizedGeo || data.length === 0) return null;

    const locations = data.map((d) => normalizeKabkotId(d.kabkot_id));
    const z = data.map((d) => d.avg_rpi);
    const text = data.map(
      (d) =>
        `${d.kabkot_name}<br>Paket: ${d.n_paket}<br>Avg RPI: ${d.avg_rpi}<br>Kritis: ${d.n_kritis}`
    );

    return {
      data: [
        {
          type: "choropleth" as const,
          geojson: normalizedGeo,
          locations,
          z,
          text,
          featureidkey: "properties.kabkot_id",
          colorscale: isDark
            ? [
                [0, "#1e293b"],
                [0.15, "#3b5278"],
                [0.35, "#6b7a8f"],
                [0.55, "#c4a35a"],
                [0.75, "#e08a3c"],
                [1, "#ef4444"],
              ]
            : [
                [0, "#e2e8f0"],
                [0.15, "#93c5fd"],
                [0.35, "#fcd34d"],
                [0.55, "#fb923c"],
                [0.75, "#f97316"],
                [1, "#ef4444"],
              ],
          zmin: 0,
          zmax: Math.max(60, ...z, 1),
          marker: { line: { width: 0.3, color: isDark ? "#64748b" : "#cbd5e1" } },
          hovertemplate: "%{text}<extra></extra>",
          colorbar: {
            tickfont: { color: colors.textPrimary },
            title: { text: "Avg RPI", font: { color: colors.textPrimary } },
          },
        },
      ],
      layout: {
        geo: {
          fitbounds: "geojson" as const,
          bgcolor: colors.chartBg,
          showframe: false,
          showcoastlines: false,
          showland: false,
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
  }, [normalizedGeo, data, isDark, colors.textPrimary, colors.chartBg]);

  if (!geojson) {
    return <div className="flex h-[480px] items-center justify-center text-muted">Memuat peta…</div>;
  }

  if (data.length === 0) {
    return (
      <div className="flex h-[480px] items-center justify-center text-muted">
        Tidak ada data geo untuk filter ini
      </div>
    );
  }

  if (!plotConfig) {
    return <div className="flex h-[480px] items-center justify-center text-muted">Memuat peta…</div>;
  }

  return (
    <div>
      <Plot
        data={plotConfig.data}
        layout={plotConfig.layout}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%", height: 480, background: colors.chartBg }}
      />
      <ColorLegend
        className="mt-2 justify-center sm:justify-start"
        items={[
          { color: isDark ? "#1e293b" : "#e2e8f0", label: "Rendah (RPI ≈ 0)" },
          { color: isDark ? "#6b7a8f" : "#fcd34d", label: "Sedang" },
          { color: isDark ? "#e08a3c" : "#f97316", label: "Tinggi" },
          { color: "#ef4444", label: "Sangat tinggi (RPI ≥ 50)" },
        ]}
      />
    </div>
  );
}
