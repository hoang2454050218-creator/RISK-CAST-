import {
  setLocale,
  formatCurrency,
  formatCurrencyRange,
  formatPercentage,
  formatNumber,
  formatDuration,
  formatDelayRange,
  formatDate,
  formatCountdown,
} from '@/lib/formatters';

beforeEach(() => {
  setLocale('en-US');
});

// ── formatCurrency ───────────────────────────────────────

describe('formatCurrency', () => {
  it('formats a basic amount without cents', () => {
    expect(formatCurrency(1000)).toBe('$1,000');
  });

  it('formats with cents when showCents is true', () => {
    expect(formatCurrency(1000.5, { showCents: true })).toBe('$1,000.50');
  });

  it('formats in compact notation', () => {
    const result = formatCurrency(1000, { compact: true });
    // Intl compact for $1000 → "$1K" (locale-dependent casing)
    expect(result).toMatch(/\$1K/i);
  });

  it('shows positive sign when signed is true', () => {
    const result = formatCurrency(1000, { signed: true });
    expect(result).toContain('+');
    expect(result).toContain('1,000');
  });

  it('formats zero correctly', () => {
    expect(formatCurrency(0)).toBe('$0');
  });
});

// ── formatCurrencyRange ──────────────────────────────────

describe('formatCurrencyRange', () => {
  it('formats a range of two currency values', () => {
    const result = formatCurrencyRange(5000, 10000);
    expect(result).toBe('$5,000 – $10,000');
  });

  it('formats a compact range', () => {
    const result = formatCurrencyRange(5000, 10000, { compact: true });
    expect(result).toMatch(/\$5K/i);
    expect(result).toMatch(/\$10K/i);
    expect(result).toContain('–');
  });
});

// ── formatPercentage ─────────────────────────────────────

describe('formatPercentage', () => {
  it('formats 0.85 as 85%', () => {
    expect(formatPercentage(0.85)).toBe('85%');
  });

  it('formats with decimal places', () => {
    expect(formatPercentage(0.8567, { decimals: 1 })).toBe('85.7%');
  });

  it('formats 1.0 as 100%', () => {
    expect(formatPercentage(1)).toBe('100%');
  });
});

// ── formatNumber ─────────────────────────────────────────

describe('formatNumber', () => {
  it('formats a basic number with commas', () => {
    expect(formatNumber(1000)).toBe('1,000');
  });

  it('formats in compact notation', () => {
    const result = formatNumber(1000, { compact: true });
    expect(result).toMatch(/1K/i);
  });

  it('formats with decimal places', () => {
    expect(formatNumber(1234.567, { decimals: 2 })).toBe('1,234.57');
  });
});

// ── formatDuration ───────────────────────────────────────

describe('formatDuration', () => {
  it('formats 1 day as singular', () => {
    expect(formatDuration(1)).toBe('1 day');
  });

  it('formats 5 days as plural', () => {
    expect(formatDuration(5)).toBe('5 days');
  });

  it('formats less than 1 day in hours when showHours is true', () => {
    // 0.5 days = 12 hours
    expect(formatDuration(0.5, { showHours: true })).toBe('12 hours');
  });

  it('formats fractional day as 1 hour singular', () => {
    // 1/24 day ≈ 1 hour
    expect(formatDuration(1 / 24, { showHours: true })).toBe('1 hour');
  });
});

// ── formatDelayRange ─────────────────────────────────────

describe('formatDelayRange', () => {
  it('formats a delay range with en-dash', () => {
    expect(formatDelayRange(7, 14)).toBe('7–14 days');
  });
});

// ── formatDate ───────────────────────────────────────────

describe('formatDate', () => {
  it('formats a known Date object', () => {
    // Use midday UTC to minimise timezone-shift issues
    const result = formatDate(new Date('2024-06-15T12:00:00Z'));
    expect(result).toContain('Jun');
    expect(result).toContain('15');
    expect(result).toContain('2024');
  });

  it('accepts a string date', () => {
    const result = formatDate('2024-06-15T12:00:00Z');
    expect(result).toContain('Jun');
    expect(result).toContain('2024');
  });
});

// ── formatCountdown ──────────────────────────────────────

describe('formatCountdown', () => {
  it('returns zeroed countdown for a past date', () => {
    const pastDate = new Date(Date.now() - 60_000);
    const result = formatCountdown(pastDate);
    // diffMs is clamped to 0 → all units are 0
    expect(result).toBe('0h 0m 0s');
  });

  it('omits seconds when showSeconds is false', () => {
    const pastDate = new Date(Date.now() - 60_000);
    const result = formatCountdown(pastDate, { showSeconds: false });
    expect(result).toBe('0h 0m');
    expect(result).not.toContain('s');
  });
});
