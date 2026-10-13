/**
 * Formatting utilities for engineering metrics and timestamps.
 */

export function formatArea(area: number, unit: string = 'm²'): string {
  return `${area.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

export function formatCurrency(amount: number, currency: string = '$'): string {
  return `${currency}${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
