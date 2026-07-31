export const CATEGORY_LABELS: Record<string, string> = {
  marketing: "集客・マーケティング",
  reservation_efficiency: "予約・業務効率",
  cost_reduction: "コスト削減",
  recruitment: "採用・人財",
  inbound: "インバウンド",
};

export const CATEGORY_COLORS: Record<string, "accent" | "success" | "warning" | "danger" | "default"> = {
  marketing: "accent",
  reservation_efficiency: "success",
  cost_reduction: "warning",
  recruitment: "danger",
  inbound: "default",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

export function categoryColor(
  category: string,
): "accent" | "success" | "warning" | "danger" | "default" {
  return CATEGORY_COLORS[category] ?? "default";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "不明";
  try {
    const date = new Date(value);
    return date.toLocaleString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "−";
  return `${Math.round(value * 100)}%`;
}
