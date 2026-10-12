/** A random source in [0, 1). Injected so that tests are deterministic. */
export type Rng = () => number;

/** Mulberry32: small, fast, seedable. */
export function seeded(seed: number): Rng {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffle<T>(items: readonly T[], rng: Rng): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

export function pick<T>(items: readonly T[], rng: Rng): T {
  if (items.length === 0) throw new Error("pick from empty list");
  return items[Math.floor(rng() * items.length)]!;
}

export function newId(rng: Rng = Math.random): string {
  return Math.floor(rng() * 2 ** 48).toString(36).padStart(10, "0");
}
