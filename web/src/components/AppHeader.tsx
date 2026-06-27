import Logo from "./Logo";

const GITHUB_URL = "https://github.com/danisharizka/auditra";

interface Props {
  isDark: boolean;
  onToggleTheme: () => void;
}

export default function AppHeader({ isDark, onToggleTheme }: Props) {
  return (
    <header className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between sm:py-5">
      <h1 className="m-0 overflow-visible leading-none">
        <Logo size="md" />
      </h1>

      <div className="flex flex-wrap items-center gap-2 sm:justify-end">
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary text-xs"
        >
          GitHub
        </a>
        <button
          type="button"
          onClick={onToggleTheme}
          className="btn-secondary flex items-center gap-1.5 text-xs"
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? "☀ Light" : "🌙 Dark"}
        </button>
        <span className="badge-pill text-xs font-bold">TA 2026</span>
        <span className="text-xs font-semibold" style={{ color: "var(--accent-live)" }}>
          ● LIVE
        </span>
      </div>
    </header>
  );
}
