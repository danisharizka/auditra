const SIRUP_URL = "https://sirup.lkpp.go.id/";
const UNIVERSITY = "Universitas Pembangunan Nasional Veteran Jawa Timur";

export default function SiteFooter() {
  return (
    <footer className="mt-8 border-t border-[var(--border-subtle)] pt-6 text-center text-[11px] leading-relaxed text-muted">
      <p className="text-primary">
        <span className="font-semibold">Auditra</span> © 2026
      </p>
      <p className="mt-1">
        Data:{" "}
        <a
          href={SIRUP_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-[var(--accent-teal,#269494)] underline-offset-2 hover:underline"
        >
          SIRUP LKPP
        </a>
        {" · "}Tim SD2026020000253
      </p>
      <p className="mt-1">
        Developed by Dani Shofi Nur Izza, Danisha Rizka Hapsari, Galih Aji Pangestu
      </p>
      <p className="mt-1 font-medium text-primary/90">{UNIVERSITY}</p>
    </footer>
  );
}
