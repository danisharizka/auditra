interface Item {
  color: string;
  label: string;
}

interface Props {
  items: Item[];
  className?: string;
}

/** Keterangan warna singkat (biru/oranye/dll.) */
export default function ColorLegend({ items, className = "" }: Props) {
  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted ${className}`}>
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 shrink-0 rounded-full border border-black/10"
            style={{ backgroundColor: item.color }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}
