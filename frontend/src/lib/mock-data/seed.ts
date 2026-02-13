/**
 * Seeded PRNG for deterministic-but-varied mock data.
 * Uses a simple mulberry32 algorithm — fast, predictable, no crypto deps.
 */

export function createSeededRandom(seed: number) {
  let state = seed;

  return {
    /** Returns a float in [0, 1) */
    next(): number {
      state |= 0;
      state = (state + 0x6d2b79f5) | 0;
      let t = Math.imul(state ^ (state >>> 15), 1 | state);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },

    /** Random integer in [min, max] inclusive */
    int(min: number, max: number): number {
      return Math.floor(this.next() * (max - min + 1)) + min;
    },

    /** Random float in [min, max) */
    float(min: number, max: number): number {
      return this.next() * (max - min) + min;
    },

    /** Pick random element from array */
    pick<T>(arr: T[]): T {
      return arr[Math.floor(this.next() * arr.length)];
    },

    /** Pick N random elements (no repeats) */
    sample<T>(arr: T[], n: number): T[] {
      const copy = [...arr];
      const result: T[] = [];
      for (let i = 0; i < Math.min(n, copy.length); i++) {
        const idx = Math.floor(this.next() * copy.length);
        result.push(copy.splice(idx, 1)[0]);
      }
      return result;
    },

    /** Boolean with given probability (0-1) */
    chance(probability: number): boolean {
      return this.next() < probability;
    },
  };
}

/** Default seed based on the day — changes daily for fresh demo data */
export function getDailySeed(): number {
  const now = new Date();
  return now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
}

export const rng = createSeededRandom(getDailySeed());
