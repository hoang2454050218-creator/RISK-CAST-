/**
 * RISKCAST Formatters
 *
 * CRITICAL: All monetary values use tabular figures for alignment
 * All values in USD unless otherwise specified
 *
 * Supports locale-aware formatting for internationalization.
 */

// Current locale - can be set globally
let currentLocale: string = 'en-US';

/**
 * Set the global locale for all formatters
 */
export function setLocale(locale: string): void {
  currentLocale = locale;
}

/**
 * Get the current locale
 */
export function getLocale(): string {
  return currentLocale;
}

/**
 * Map locale codes to Intl locale strings
 */
function getIntlLocale(locale?: string): string {
  const l = locale || currentLocale;
  // Map common codes
  if (l === 'vi') return 'vi-VN';
  if (l === 'en') return 'en-US';
  return l;
}

/**
 * Format currency with optional confidence interval
 */
export function formatCurrency(
  amount: number | null | undefined,
  options?: {
    showCents?: boolean;
    compact?: boolean;
    signed?: boolean;
    locale?: string;
  },
): string {
  if (amount == null || isNaN(amount)) return '—';
  const { showCents = false, compact = false, signed = false, locale } = options ?? {};

  const formatter = new Intl.NumberFormat(getIntlLocale(locale), {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
    notation: compact ? 'compact' : 'standard',
    signDisplay: signed ? 'always' : 'auto',
  });

  return formatter.format(amount);
}

/**
 * Format a currency range (e.g., confidence interval)
 */
export function formatCurrencyRange(
  min: number,
  max: number,
  options?: { compact?: boolean; locale?: string },
): string {
  const { compact = false, locale } = options ?? {};
  return `${formatCurrency(min, { compact, locale })} – ${formatCurrency(max, { compact, locale })}`;
}

/**
 * Format percentage
 */
export function formatPercentage(
  value: number | null | undefined,
  options?: { decimals?: number; locale?: string },
): string {
  if (value == null || isNaN(value)) return '—';
  const { decimals = 0, locale } = options ?? {};

  const formatter = new Intl.NumberFormat(getIntlLocale(locale), {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return formatter.format(value);
}

/**
 * Format a number with commas
 */
export function formatNumber(
  value: number | null | undefined,
  options?: { decimals?: number; compact?: boolean; locale?: string },
): string {
  if (value == null || isNaN(value)) return '—';
  const { decimals = 0, compact = false, locale } = options ?? {};

  const formatter = new Intl.NumberFormat(getIntlLocale(locale), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    notation: compact ? 'compact' : 'standard',
  });

  return formatter.format(value);
}

/**
 * Duration labels by locale
 */
const durationLabels: Record<string, { day: string; days: string; hour: string; hours: string }> = {
  en: { day: 'day', days: 'days', hour: 'hour', hours: 'hours' },
  vi: { day: 'ngày', days: 'ngày', hour: 'giờ', hours: 'giờ' },
};

/**
 * Format days/hours for delays
 */
export function formatDuration(
  days: number,
  options?: { showHours?: boolean; locale?: string },
): string {
  const { showHours = false, locale } = options ?? {};
  const l = (locale || currentLocale).split('-')[0];
  const labels = durationLabels[l] || durationLabels.en;

  if (days < 1 && showHours) {
    const hours = Math.round(days * 24);
    return `${hours} ${hours === 1 ? labels.hour : labels.hours}`;
  }

  const roundedDays = Math.round(days);
  return `${roundedDays} ${roundedDays === 1 ? labels.day : labels.days}`;
}

/**
 * Format a delay range (e.g., "7-14 days")
 */
export function formatDelayRange(
  minDays: number,
  maxDays: number,
  options?: { locale?: string },
): string {
  const { locale } = options ?? {};
  const l = (locale || currentLocale).split('-')[0];
  const labels = durationLabels[l] || durationLabels.en;

  return `${Math.round(minDays)}–${Math.round(maxDays)} ${labels.days}`;
}

/**
 * Format date for display
 */
export function formatDate(
  date: Date | string,
  options?: { includeTime?: boolean; relative?: boolean; locale?: string },
): string {
  const { includeTime = false, relative = false, locale } = options ?? {};
  const d = typeof date === 'string' ? new Date(date) : date;

  if (relative) {
    return formatRelativeTime(d, { locale });
  }

  const dateFormatter = new Intl.DateTimeFormat(getIntlLocale(locale), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...(includeTime && {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }),
  });

  return dateFormatter.format(d);
}

/**
 * Format relative time (e.g., "2 hours ago", "in 3 days")
 */
export function formatRelativeTime(date: Date, options?: { locale?: string }): string {
  const { locale } = options ?? {};
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffSeconds = Math.round(diffMs / 1000);
  const diffMinutes = Math.round(diffSeconds / 60);
  const diffHours = Math.round(diffMinutes / 60);
  const diffDays = Math.round(diffHours / 24);

  const rtf = new Intl.RelativeTimeFormat(getIntlLocale(locale), { numeric: 'auto' });

  if (Math.abs(diffSeconds) < 60) {
    return rtf.format(diffSeconds, 'second');
  }
  if (Math.abs(diffMinutes) < 60) {
    return rtf.format(diffMinutes, 'minute');
  }
  if (Math.abs(diffHours) < 24) {
    return rtf.format(diffHours, 'hour');
  }
  return rtf.format(diffDays, 'day');
}

/**
 * Format countdown time (HH:MM:SS or similar)
 */
export function formatCountdown(
  targetDate: Date,
  options?: { showSeconds?: boolean; locale?: string },
): string {
  const { showSeconds = true, locale } = options ?? {};
  const l = (locale || currentLocale).split('-')[0];

  const now = new Date();
  const diffMs = Math.max(0, targetDate.getTime() - now.getTime());

  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  // Localized time units
  const units = {
    en: { d: 'd', h: 'h', m: 'm', s: 's' },
    vi: { d: 'ng', h: 'g', m: 'ph', s: 'gy' },
  };
  const u = units[l as keyof typeof units] || units.en;

  let result = '';
  if (days > 0) result += `${days}${u.d} `;
  result += `${hours}${u.h} ${minutes}${u.m}`;
  if (showSeconds) result += ` ${seconds}${u.s}`;

  return result.trim();
}

/**
 * Shipment labels by locale
 */
const shipmentLabels: Record<string, { one: string; many: string }> = {
  en: { one: 'shipment', many: 'shipments' },
  vi: { one: 'lô hàng', many: 'lô hàng' },
};

/**
 * Format shipment/container count
 */
export function formatShipmentCount(count: number, options?: { locale?: string }): string {
  const { locale } = options ?? {};
  const l = (locale || currentLocale).split('-')[0];
  const labels = shipmentLabels[l] || shipmentLabels.en;

  return `${count} ${count === 1 ? labels.one : labels.many}`;
}

/**
 * Format TEU count
 */
export function formatTEU(teu: number, options?: { locale?: string }): string {
  return `${formatNumber(teu, options)} TEU`;
}

/**
 * Hook for getting locale-aware formatters
 * Usage: const { formatCurrency } = useFormatters();
 */
export function createLocaleFormatters(locale: string) {
  return {
    formatCurrency: (amount: number, opts?: Parameters<typeof formatCurrency>[1]) =>
      formatCurrency(amount, { ...opts, locale }),
    formatCurrencyRange: (
      min: number,
      max: number,
      opts?: Parameters<typeof formatCurrencyRange>[2],
    ) => formatCurrencyRange(min, max, { ...opts, locale }),
    formatPercentage: (value: number, opts?: Parameters<typeof formatPercentage>[1]) =>
      formatPercentage(value, { ...opts, locale }),
    formatNumber: (value: number, opts?: Parameters<typeof formatNumber>[1]) =>
      formatNumber(value, { ...opts, locale }),
    formatDuration: (days: number, opts?: Parameters<typeof formatDuration>[1]) =>
      formatDuration(days, { ...opts, locale }),
    formatDelayRange: (
      minDays: number,
      maxDays: number,
      opts?: Parameters<typeof formatDelayRange>[2],
    ) => formatDelayRange(minDays, maxDays, { ...opts, locale }),
    formatDate: (date: Date | string, opts?: Parameters<typeof formatDate>[1]) =>
      formatDate(date, { ...opts, locale }),
    formatRelativeTime: (date: Date, opts?: Parameters<typeof formatRelativeTime>[1]) =>
      formatRelativeTime(date, { ...opts, locale }),
    formatCountdown: (targetDate: Date, opts?: Parameters<typeof formatCountdown>[1]) =>
      formatCountdown(targetDate, { ...opts, locale }),
    formatShipmentCount: (count: number, opts?: Parameters<typeof formatShipmentCount>[1]) =>
      formatShipmentCount(count, { ...opts, locale }),
    formatTEU: (teu: number, opts?: Parameters<typeof formatTEU>[1]) =>
      formatTEU(teu, { ...opts, locale }),
  };
}
