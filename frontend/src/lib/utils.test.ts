import { cn, clamp, isDefined, safeJsonParse, generateId } from '@/lib/utils';

// ── cn ───────────────────────────────────────────────────

describe('cn', () => {
  it('merges class strings', () => {
    expect(cn('text-red-500', 'bg-blue-500')).toBe('text-red-500 bg-blue-500');
  });

  it('deduplicates conflicting Tailwind classes', () => {
    // tailwind-merge keeps the last conflicting utility
    expect(cn('p-4', 'p-2')).toBe('p-2');
  });

  it('handles conditional classes', () => {
    const isActive = true;
    const result = cn('base', isActive && 'active');
    expect(result).toBe('base active');
  });

  it('filters out falsy values', () => {
    const result = cn('base', false && 'hidden', undefined, null);
    expect(result).toBe('base');
  });
});

// ── clamp ────────────────────────────────────────────────

describe('clamp', () => {
  it('clamps a value below min to min', () => {
    expect(clamp(-5, 0, 10)).toBe(0);
  });

  it('clamps a value above max to max', () => {
    expect(clamp(15, 0, 10)).toBe(10);
  });

  it('returns the value when within range', () => {
    expect(clamp(5, 0, 10)).toBe(5);
  });

  it('returns min when value equals min', () => {
    expect(clamp(0, 0, 10)).toBe(0);
  });

  it('returns max when value equals max', () => {
    expect(clamp(10, 0, 10)).toBe(10);
  });
});

// ── isDefined ────────────────────────────────────────────

describe('isDefined', () => {
  it('returns true for non-null/non-undefined values', () => {
    expect(isDefined(42)).toBe(true);
    expect(isDefined('hello')).toBe(true);
    expect(isDefined(0)).toBe(true);
    expect(isDefined('')).toBe(true);
    expect(isDefined(false)).toBe(true);
  });

  it('returns false for null', () => {
    expect(isDefined(null)).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(isDefined(undefined)).toBe(false);
  });
});

// ── safeJsonParse ────────────────────────────────────────

describe('safeJsonParse', () => {
  it('parses valid JSON and returns the result', () => {
    const result = safeJsonParse('{"key":"value"}', { key: 'default' });
    expect(result).toEqual({ key: 'value' });
  });

  it('returns fallback for invalid JSON', () => {
    const fallback = { fallback: true };
    const result = safeJsonParse('not valid json', fallback);
    expect(result).toEqual({ fallback: true });
  });

  it('returns fallback for empty string', () => {
    const result = safeJsonParse('', 'default-value');
    expect(result).toBe('default-value');
  });
});

// ── generateId ───────────────────────────────────────────

describe('generateId', () => {
  it('returns a string of length 9', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
    expect(id).toHaveLength(9);
  });

  it('generates unique ids', () => {
    const ids = new Set(Array.from({ length: 50 }, () => generateId()));
    expect(ids.size).toBe(50);
  });
});
