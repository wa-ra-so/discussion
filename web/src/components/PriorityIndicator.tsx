const MAX_PRIORITY = 5;

export function PriorityIndicator({
  value,
  max = MAX_PRIORITY,
}: {
  value: number | null | undefined;
  max?: number;
}) {
  if (!value) return null;

  return (
    <span
      role="img"
      aria-label={`優先度 ${value}/${max}`}
      className="inline-flex items-center gap-0.5"
    >
      {Array.from({ length: max }, (_, i) => (
        <span
          key={i}
          aria-hidden="true"
          className={`h-2 w-2 rounded-full transition-colors ${
            i < value ? "bg-[var(--danger)]" : "bg-[var(--border)]"
          }`}
        />
      ))}
    </span>
  );
}
