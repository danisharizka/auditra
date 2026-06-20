/** Normalize kab/kota BPS code so API numbers match GeoJSON string properties. */
export function normalizeKabkotId(id: string | number | null | undefined): string {
  if (id == null || id === "") return "";
  const n = typeof id === "number" ? id : parseFloat(String(id).trim());
  if (!Number.isFinite(n)) return String(id);
  return n.toFixed(2);
}
