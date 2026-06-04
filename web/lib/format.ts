export function formatMoney(cents?: number | null): string {
  if (cents === null || cents === undefined) return "-";
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}$${(abs / 100).toFixed(2)}`;
}

export function formatBps(bps?: number | null): string {
  if (bps === null || bps === undefined) return "-";
  return `${(bps / 100).toFixed(2)}%`;
}

export function signedBpsClass(bps?: number | null): string {
  if (bps === null || bps === undefined || bps === 0) return "numeric";
  return bps > 0 ? "numeric positive" : "numeric negative";
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export function formatShortDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatQuantity(value?: number | string | null): string {
  if (value === null || value === undefined) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return numeric.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  });
}

export function pnlClass(cents?: number | null): string {
  if (cents === null || cents === undefined || cents === 0) return "money";
  return cents > 0 ? "money positive" : "money negative";
}

export function statusClass(status?: string | null): string {
  if (!status) return "pill";
  const normalized = status.toLowerCase().replaceAll("_", "-");
  return `pill status-${normalized}`;
}
