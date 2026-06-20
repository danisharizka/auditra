import ReactECharts from "echarts-for-react";
import { useTheme } from "../theme/ThemeContext";

const RISK_COLORS: Record<string, string> = {
  KRITIS: "#ef4444",
  TINGGI: "#f97316",
  SEDANG: "#eab308",
  RENDAH: "#3b82f6",
};

export function RiskDonut({ data }: { data: { risk_label: string; count: number }[] }) {
  const { colors, mode } = useTheme();
  const order = ["KRITIS", "TINGGI", "SEDANG", "RENDAH"];
  const sorted = [...data].sort(
    (a, b) => order.indexOf(a.risk_label) - order.indexOf(b.risk_label)
  );

  const option = {
    backgroundColor: colors.chartBg,
    tooltip: { trigger: "item", backgroundColor: colors.bgPanel, textStyle: { color: colors.textPrimary } },
    series: [
      {
        type: "pie",
        radius: ["55%", "75%"],
        label: { color: colors.textPrimary, formatter: "{b}\n{d}%" },
        data: sorted.map((d) => ({
          name: d.risk_label,
          value: d.count,
          itemStyle: { color: RISK_COLORS[d.risk_label] || "#64748b" },
        })),
      },
    ],
  };

  return <ReactECharts key={mode} option={option} style={{ height: 240, background: colors.chartBg }} notMerge />;
}

export function MetodeBar({
  data,
}: {
  data: { metode: string; jumlah: number; avg_rpi: number }[];
}) {
  const { colors, mode } = useTheme();
  const sorted = [...data].sort((a, b) => a.avg_rpi - b.avg_rpi);
  const option = {
    backgroundColor: colors.chartBg,
    grid: { left: 140, right: 40, top: 10, bottom: 30 },
    tooltip: { trigger: "axis", backgroundColor: colors.bgPanel, textStyle: { color: colors.textPrimary } },
    xAxis: {
      type: "value",
      axisLabel: { color: colors.chartText },
      splitLine: { lineStyle: { color: colors.chartGrid } },
    },
    yAxis: {
      type: "category",
      data: sorted.map((d) => d.metode),
      axisLabel: { color: colors.chartText, width: 130, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: sorted.map((d) => ({
          value: d.avg_rpi,
          itemStyle: { color: d.avg_rpi >= 30 ? colors.accentOrange : colors.accentBlue },
        })),
        label: { show: true, position: "right", color: colors.textPrimary, formatter: "{c}" },
      },
    ],
  };
  return <ReactECharts key={mode} option={option} style={{ height: 280, background: colors.chartBg }} notMerge />;
}

export function ScatterChart({
  points,
}: {
  points: { pagu_miliar: number; RPI: number; risk_label: string }[];
}) {
  const { colors, mode } = useTheme();
  const groups = ["KRITIS", "TINGGI", "SEDANG", "RENDAH"];
  const series = groups.map((label) => ({
    name: label,
    type: "scatter",
    symbolSize: 8,
    itemStyle: { color: RISK_COLORS[label], opacity: 0.65 },
    data: points
      .filter((p) => p.risk_label === label)
      .map((p) => [p.pagu_miliar, p.RPI]),
  }));

  const option = {
    backgroundColor: colors.chartBg,
    legend: { textStyle: { color: colors.chartText }, top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    tooltip: { trigger: "item", backgroundColor: colors.bgPanel, textStyle: { color: colors.textPrimary } },
    xAxis: {
      name: "Pagu (Miliar)",
      nameTextStyle: { color: colors.chartText },
      axisLabel: { color: colors.chartText },
      splitLine: { lineStyle: { color: colors.chartGrid } },
    },
    yAxis: {
      name: "RPI",
      nameTextStyle: { color: colors.chartText },
      axisLabel: { color: colors.chartText },
      splitLine: { lineStyle: { color: colors.chartGrid } },
    },
    series,
  };
  return <ReactECharts key={mode} option={option} style={{ height: 320, background: colors.chartBg }} notMerge />;
}

export function RadarChart({ signals }: { signals: Record<string, number> }) {
  const { colors, isDark, mode } = useTheme();
  const keys = Object.keys(signals);
  const values = Object.values(signals);
  const max = Math.max(...values, 0.001);
  const option = {
    backgroundColor: colors.chartBg,
    radar: {
      indicator: keys.map((k) => ({ name: k, max: max * 1.1 })),
      axisName: { color: colors.chartText },
      splitLine: { lineStyle: { color: colors.chartGrid } },
      splitArea: {
        areaStyle: {
          color: isDark
            ? ["rgba(30,41,59,0.4)", "rgba(30,41,59,0.2)"]
            : ["rgba(226,232,240,0.6)", "rgba(241,245,249,0.9)"],
        },
      },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            areaStyle: { color: "rgba(249,115,22,0.25)" },
            lineStyle: { color: colors.accentOrange },
            itemStyle: { color: colors.accentOrange },
          },
        ],
      },
    ],
  };
  return <ReactECharts key={mode} option={option} style={{ height: 260, background: colors.chartBg }} notMerge />;
}
