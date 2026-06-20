import type { Filters } from "../types";

interface Props {
  filters: Filters;
  onChange: (next: Partial<Filters>) => void;
  options: { lembaga: string[]; metode: string[]; provinsi: string[] };
}

export default function FilterBar({ filters, onChange, options }: Props) {
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-4">
      <div>
        <p className="mb-1 text-[10px] uppercase tracking-wide text-muted">Provinsi</p>
        <select
          className="input-select"
          value={filters.provinsi}
          onChange={(e) => onChange({ provinsi: e.target.value })}
        >
          <option value="ALL">Semua Provinsi</option>
          {options.provinsi.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>
      <div>
        <p className="mb-1 text-[10px] uppercase tracking-wide text-muted">Lembaga</p>
        <select
          className="input-select"
          value={filters.lembaga}
          onChange={(e) => onChange({ lembaga: e.target.value })}
        >
          <option value="ALL">Semua Lembaga</option>
          {options.lembaga.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>
      <div>
        <p className="mb-1 text-[10px] uppercase tracking-wide text-muted">Metode</p>
        <select
          className="input-select"
          value={filters.metode}
          onChange={(e) => onChange({ metode: e.target.value })}
        >
          <option value="ALL">Semua Metode</option>
          {options.metode.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>
      <div>
        <p className="mb-1 text-[10px] uppercase tracking-wide text-muted">Min. RPI</p>
        <select
          className="input-select"
          value={filters.riskMin}
          onChange={(e) => onChange({ riskMin: Number(e.target.value) })}
        >
          <option value={0}>Semua</option>
          <option value={30}>≥30 Sedang+</option>
          <option value={50}>≥50 Tinggi+</option>
          <option value={70}>≥70 Kritis</option>
        </select>
      </div>
    </div>
  );
}
