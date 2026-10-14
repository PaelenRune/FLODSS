/**
 * Formatting utilities for engineering metrics, costs, and spatial units.
 * Adheres strictly to scientific precision standards and currency neutrality.
 */

export function formatArea(area: number, unit: string = 'm²'): string {
  return `${area.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unit}`;
}

/**
 * Format cost values without arbitrarily assuming USD '$'.
 * Uses problem currency if defined; otherwise outputs clean formatted numeric cost units.
 */
export function formatCost(amount: number | undefined | null, currency?: string | null): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '—';
  const numStr = amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (currency && currency.trim().length > 0) {
    return `${currency.trim()}${numStr}`;
  }
  return numStr;
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Format percentage points difference.
 */
export function formatPercentagePoints(delta: number): string {
  const sign = delta > 0 ? '+' : '';
  return `${sign}${delta.toFixed(2)} %p`;
}
