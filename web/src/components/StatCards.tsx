import type { OverviewStats } from "../types";

const cards = (
  stats: OverviewStats | null
): { title: string; value: string; sub: string; accent: string }[] => [
  {
    title: "Total Paket",
    value: stats ? stats.total_paket.toLocaleString("id-ID") : "—",
    sub: "dalam filter (dari dataset penuh)",
    accent: "border-blue-500",
  },
  {
    title: "Total Pagu",
    value: stats ? `Rp ${stats.total_pagu_miliar.toLocaleString("id-ID")} M` : "—",
    sub: "miliar rupiah",
    accent: "border-blue-500",
  },
  {
    title: "Paket Kritis",
    value: stats ? stats.paket_kritis.toLocaleString("id-ID") : "—",
    sub: "RPI ≥ 70",
    accent: "border-orange-500",
  },
  {
    title: "Rata-rata RPI",
    value: stats ? stats.avg_rpi.toFixed(1) : "—",
    sub: "skala 0–100",
    accent: "border-yellow-500",
  },
  {
    title: "Potensi Split Contract",
    value: stats ? stats.split_contract.toLocaleString("id-ID") : "—",
    sub: "similarity ≥ 0.6",
    accent: "border-orange-500",
  },
];

export default function StatCards({ stats }: { stats: OverviewStats | null }) {
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {cards(stats).map((c) => (
        <div key={c.title} className={`stat-card ${c.accent}`}>
          <p className="text-[11px] uppercase tracking-wide text-muted">{c.title}</p>
          <p className="mt-1 text-2xl font-extrabold text-primary">{c.value}</p>
          <p className="text-[11px] text-muted">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}
