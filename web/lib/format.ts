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

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

