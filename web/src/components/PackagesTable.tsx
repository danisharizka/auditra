import type { PaginatedPackages } from "../types";

interface Props {
  result: PaginatedPackages | null;
  page: number;
  loading?: boolean;
  onPage: (p: number) => void;
}

export default function PackagesTable({ result, page, loading, onPage }: Props) {
  if (!result && loading) {
    return <div className="text-muted">Memuat tabel…</div>;
  }

  if (!result) {
    return <div className="text-muted">Tidak ada data.</div>;
  }

  return (
    <div>
      <p className="mb-3 text-xs text-muted">
        Menampilkan halaman {result.page} dari {result.total_pages} —{" "}
        <strong className="text-primary">{result.total.toLocaleString("id-ID")}</strong> paket
        match filter (semua baris dapat diakses via pagination).
        {loading && (
          <span className="ml-2 font-medium" style={{ color: "var(--accent-loading)" }}>
            Memuat…
          </span>
        )}
      </p>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>RPI</th>
              <th>Label</th>
              <th>Paket</th>
              <th>Lembaga</th>
              <th>Metode</th>
              <th>Pagu (M)</th>
              <th>Lokasi</th>
            </tr>
          </thead>
          <tbody>
            {result.data.map((row) => {
              const label = String(row.risk_label || "");
              const rowClass =
                label === "KRITIS" ? "row-kriti" : label === "TINGGI" ? "row-tinggi" : "";
              return (
                <tr key={String(row.id)} className={rowClass}>
                  <td className="font-semibold">{Number(row.RPI).toFixed(1)}</td>
                  <td>{label}</td>
                  <td className="max-w-xs truncate" title={String(row.paket)}>
                    {String(row.paket)}
                  </td>
                  <td className="max-w-[180px] truncate">{String(row.lembaga)}</td>
                  <td>{String(row.metode)}</td>
                  <td>
                    {row.pagu_miliar != null
                      ? Number(row.pagu_miliar).toFixed(2)
                      : row.pagu != null
                        ? (Number(row.pagu) / 1e9).toFixed(2)
                        : "—"}
                  </td>
                  <td className="max-w-[200px] truncate">{String(row.lokasi || "")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          disabled={page <= 1 || loading}
          onClick={() => onPage(page - 1)}
          className="btn-secondary text-sm"
        >
          ← Sebelumnya
        </button>
        <span className="text-sm text-muted">
          Halaman {page} / {result.total_pages}
        </span>
        <button
          type="button"
          disabled={page >= result.total_pages || loading}
          onClick={() => onPage(page + 1)}
          className="btn-secondary text-sm"
        >
          Selanjutnya →
        </button>
      </div>
    </div>
  );
}
