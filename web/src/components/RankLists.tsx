import type { RankRow } from "../types";

function Row({ name, row }: { name: string; row: RankRow }) {
  const isHigh = row.avg_rpi >= 30;
  return (
    <div className="rank-row">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-primary">{name}</span>
        <span
          className="rank-badge"
          style={{ color: isHigh ? "var(--accent-orange)" : "var(--accent-blue)" }}
        >
          RPI {row.avg_rpi.toFixed(1)}
        </span>
      </div>
      <div className="mt-1 text-[11px] text-muted">
        <span className="mr-3" style={{ color: "var(--accent-orange)" }}>
          Kritis: {row.n_kritis}
        </span>
        <span className="mr-3" style={{ color: "var(--accent-live)" }}>
          Tinggi: {row.n_tinggi}
        </span>
        <span>Total paket: {row.n_paket.toLocaleString("id-ID")}</span>
      </div>
    </div>
  );
}

export function RankLembaga({ data }: { data: RankRow[] }) {
  return (
    <div>
      {data.map((r) => (
        <Row key={r.lembaga} name={r.lembaga || "—"} row={r} />
      ))}
    </div>
  );
}

export function RankProvinsi({ data }: { data: RankRow[] }) {
  return (
    <div>
      {data.map((r) => (
        <Row key={r.prov_name} name={r.prov_name || "—"} row={r} />
      ))}
    </div>
  );
}
