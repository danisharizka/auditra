import { formatPaguCompact } from "../utils/formatPagu";
import type { GeoCoverage, OverviewStats } from "../types";

interface Props {
  stats: OverviewStats | null;
  geoCoverage: GeoCoverage | null;
}

export default function StatCards({ stats, geoCoverage }: Props) {
  const mapped = geoCoverage?.mapped_packages ?? 0;
  const total = geoCoverage?.total_packages ?? 0;
  const unmapped = geoCoverage?.unmapped_packages ?? 0;
  const multi = geoCoverage?.multi_lokasi_packages ?? 0;

  return (
    <div className="mb-4 grid grid-cols-1 gap-3 lg:grid-cols-12">
      <div className="stat-card border-blue-500 lg:col-span-4">
        <p className="text-[11px] uppercase tracking-wide text-muted">Total Pagu (filter)</p>
        <p className="mt-1 text-3xl font-extrabold text-primary">
          {stats ? formatPaguCompact(stats.total_pagu_miliar) : "—"}
        </p>
        <p className="text-[11px] text-muted">
          Akumulasi pagu paket dalam filter aktif · prioritas audit via RPI
        </p>
      </div>

      <div className="stat-card border-blue-500 lg:col-span-4">
        <p className="text-[11px] uppercase tracking-wide text-muted">Paket Terpetakan</p>
        <p className="mt-1 text-3xl font-extrabold text-primary">
          {total > 0 ? (
            <>
              {mapped.toLocaleString("id-ID")}
              <span className="text-lg font-semibold text-muted"> / {total.toLocaleString("id-ID")}</span>
            </>
          ) : (
            "—"
          )}
        </p>
        <p className="text-[11px] text-muted">
          {unmapped.toLocaleString("id-ID")} unmapped · {multi.toLocaleString("id-ID")} multi-lokasi
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:col-span-4">
        {[
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
            title: "Split Contract",
            value: stats ? stats.split_contract.toLocaleString("id-ID") : "—",
            sub: "fragmentasi ≥ 0.6",
            accent: "border-orange-500",
          },
        ].map((c) => (
          <div key={c.title} className={`stat-card ${c.accent}`}>
            <p className="text-[10px] uppercase tracking-wide text-muted">{c.title}</p>
            <p className="mt-1 text-xl font-extrabold text-primary">{c.value}</p>
            <p className="text-[10px] text-muted">{c.sub}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
