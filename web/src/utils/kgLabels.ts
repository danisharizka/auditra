/** Label & relasi KG — penamaan seragam untuk dashboard. */

const RELATION_ID: Record<string, string> = {
  HAS_SATKER: "Memiliki satker",
  USES_METHOD: "Menggunakan metode",
  PROCURES: "Mengadaan jenis",
  OPERATES_IN: "Beroperasi di provinsi",
};

const TYPE_ID: Record<string, string> = {
  lembaga: "Lembaga",
  satker: "Satker",
  metode: "Metode",
  jenis: "Jenis pengadaan",
  provinsi: "Provinsi",
};

/** Ubah label ALL CAPS (umum di data SIRUP) ke title case. */
export function normalizeDisplayCase(text: string): string {
  const s = text.trim();
  if (!s) return s;
  const letters = s.replace(/[^A-Za-zÀ-ÿ]/g, "");
  if (letters.length >= 4 && letters === letters.toUpperCase()) {
    return s
      .toLowerCase()
      .split(/(\s+|\/|-)/)
      .map((part) => {
        if (/^\s+$|^\/$|^-$/.test(part)) return part;
        return part.charAt(0).toUpperCase() + part.slice(1);
      })
      .join("");
  }
  return s;
}

export function formatNodeLabel(raw: unknown, nodeType?: unknown): string {
  const s = String(raw ?? "").trim();
  const stripped = s.replace(/^(L|SK|M|J|P)::/, "");
  void nodeType;
  return normalizeDisplayCase(stripped);
}

export function nodeTypeLabel(nodeType: unknown): string {
  return TYPE_ID[String(nodeType)] ?? "Entitas";
}

export function formatRelation(relation: unknown): string {
  const key = String(relation ?? "");
  if (RELATION_ID[key]) return RELATION_ID[key];
  const raw = key.replace(/_/g, " ").toLowerCase();
  return raw ? raw.charAt(0).toUpperCase() + raw.slice(1) : raw;
}

export function isHighRisk(avgRpi: unknown): boolean {
  return Number(avgRpi) >= 30;
}
