/** Daily activity: how many answers the learner gave on each local calendar day. */
export type Activity = Record<string, number>;

const pad = (n: number) => String(n).padStart(2, "0");

export function dayKey(ms: number): string {
  const d = new Date(ms);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function previousDay(key: string): string {
  const [y, m, d] = key.split("-").map(Number) as [number, number, number];
  return dayKey(new Date(y, m - 1, d - 1, 12).getTime());
}

/**
 * Consecutive days with at least one answer, ending today. A streak that ended
 * yesterday still counts (the learner can keep it alive today).
 */
export function streak(activity: Activity, now: number): number {
  let day = dayKey(now);
  if (!activity[day]) day = previousDay(day);
  let n = 0;
  while (activity[day]) {
    n += 1;
    day = previousDay(day);
  }
  return n;
}

export function bump(activity: Activity, now: number, by = 1, keepDays = 120): Activity {
  const key = dayKey(now);
  const next: Activity = { ...activity, [key]: (activity[key] ?? 0) + by };
  const keys = Object.keys(next).sort();
  for (const old of keys.slice(0, Math.max(0, keys.length - keepDays))) delete next[old];
  return next;
}
