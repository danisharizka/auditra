/** Label & relasi KG — penamaan seragam untuk dashboard. */

const RELATION_ID: Record<string, string> = {
  HAS_SATKER: "memiliki Satker",
  USES_METHOD: "menggunakan Metode",
  PROCURES: "mengadaan Jenis",
  OPERATES_IN: "beroperasi di Provinsi",
};

const TYPE_ID: Record<string, string> = {
  lembaga: "Lembaga",
  satker: "Satker",
  metode: "Metode",
  jenis: "Jenis Pengadaan",
  provinsi: "Provinsi",
};

export function formatNodeLabel(raw: unknown, nodeType?: unknown): string {
  const s = String(raw ?? "").trim();
  const stripped = s.replace(/^(L|SK|M|J|P)::/, "");
  if (nodeType && TYPE_ID[String(nodeType)]) {
    return stripped;
  }
  return stripped;
}

export function nodeTypeLabel(nodeType: unknown): string {
  return TYPE_ID[String(nodeType)] ?? "Entitas";
}

export function formatRelation(relation: unknown): string {
  const key = String(relation ?? "");
  return RELATION_ID[key] ?? key.replace(/_/g, " ").toLowerCase();
}

export function isHighRisk(avgRpi: unknown): boolean {
  return Number(avgRpi) >= 30;
}
