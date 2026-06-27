interface Props {
  showWordmark?: boolean;
  size?: "sm" | "md" | "lg";
}

const iconSizes = {
  sm: "h-9 w-9",
  md: "h-10 w-10",
  lg: "h-12 w-12",
};

const textSizes = {
  sm: "text-sm tracking-[0.18em]",
  md: "text-base tracking-[0.2em] sm:text-lg",
  lg: "text-lg tracking-[0.22em] sm:text-xl",
};

export default function Logo({ showWordmark = true, size = "md" }: Props) {
  return (
    <div className="flex items-center gap-2.5">
      <img
        src="/logo-icon.png?v=7"
        alt=""
        className={`${iconSizes[size]} shrink-0 rounded-lg bg-white object-contain object-center shadow-sm ring-1 ring-black/5 dark:ring-white/10`}
        width={40}
        height={40}
        decoding="async"
      />

      {showWordmark && (
        <span className={`font-extrabold leading-none text-primary ${textSizes[size]}`}>
          AUDITRA
        </span>
      )}
    </div>
  );
}
