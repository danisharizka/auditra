/** Format nilai pagu (satuan: miliar rupiah, dari SUM(pagu)/1e9). */
export function formatPaguCompact(miliar: number): string {
  if (!Number.isFinite(miliar) || miliar <= 0) return "Rp 0";
  if (miliar >= 1_000) return `Rp ${(miliar / 1_000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} T`;
  if (miliar >= 1) return `Rp ${miliar.toLocaleString("id-ID", { maximumFractionDigits: 1 })} M`;
  if (miliar >= 0.001) return `Rp ${(miliar * 1_000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt`;
  return `Rp ${(miliar * 1_000_000).toLocaleString("id-ID", { maximumFractionDigits: 0 })} rb`;
}
