import { parseState, type ActiveSession, type LessonResult, type ProgressState, type SessionSummary } from "../lib/progress";
import type { ItemProgress } from "../lib/srs";

const MAX_HISTORY = 30;

function newerItem(a: ItemProgress, b: ItemProgress): ItemProgress {
  if (a.lastSeenAt !== b.lastSeenAt) return a.lastSeenAt > b.lastSeenAt ? a : b;
  return a.seen >= b.seen ? a : b;
}

function mergeLesson(a: LessonResult, b: LessonResult): LessonResult {
  const done = [a.completedAt, b.completedAt].filter((x): x is number => x !== null);
  const best = a.bestScore >= b.bestScore ? a : b;
  return {
    completedAt: done.length ? Math.min(...done) : null,
    bestScore: best.bestScore,
    total: best.total,
    attempts: Math.max(a.attempts, b.attempts),
  };
}

function lastTouched(s: ActiveSession): number {
  return Math.max(s.startedAt, ...s.answers.map((a) => a.at));
}

function mergeActive(a: ActiveSession | null, b: ActiveSession | null, finished: Set<string>): ActiveSession | null {
  const live = [a, b].filter((s): s is ActiveSession => s !== null && !finished.has(s.id));
  if (live.length === 0) return null;
  if (live.length === 1) return live[0]!;
  const [x, y] = live as [ActiveSession, ActiveSession];
  if (x.id === y.id) return x.answers.length !== y.answers.length ? (x.answers.length > y.answers.length ? x : y) : (x.cursor >= y.cursor ? x : y);
  return lastTouched(x) >= lastTouched(y) ? x : y;
}

function mergeMap<T>(a: Record<string, T>, b: Record<string, T>, pick: (x: T, y: T) => T): Record<string, T> {
  const out: Record<string, T> = { ...a };
  for (const [k, v] of Object.entries(b)) out[k] = k in out ? pick(out[k]!, v) : v;
  return out;
}

/**
 * Combines progress from two devices using bounded, last-write-wins summaries: the most recent answer wins per item,
 * lesson results keep their best, histories are unioned, and daily activity keeps the larger count.
 */
export function mergeProgress(local: ProgressState, remote: ProgressState): ProgressState {
  local = parseState(JSON.stringify(local));
  remote = parseState(JSON.stringify(remote));
  const sessionsById = new Map<string, SessionSummary>();
  for (const s of [...local.sessions, ...remote.sessions]) sessionsById.set(s.id, s);
  const sessions = [...sessionsById.values()].sort((a, b) => b.finishedAt - a.finishedAt).slice(0, MAX_HISTORY);
  const merged: ProgressState = {
    version: local.version,
    items: mergeMap(local.items, remote.items, newerItem),
    lessons: mergeMap(local.lessons, remote.lessons, mergeLesson),
    sessions,
    activeSession: mergeActive(local.activeSession, remote.activeSession, new Set(sessionsById.keys())),
    lessonDrafts: mergeMap(local.lessonDrafts ?? {}, remote.lessonDrafts ?? {}, (a, b) => a.updatedAt >= b.updatedAt ? a : b),
    activity: mergeMap(local.activity, remote.activity, (x, y) => Math.max(x, y)),
    updatedAt: Math.max(local.updatedAt, remote.updatedAt),
  };
  // Round-trip through the validator so a malformed remote copy can never enter the store.
  return parseState(JSON.stringify(merged));
}

/** True when the two states hold the same learning data (ignoring the change timestamp). */
export function sameProgress(a: ProgressState, b: ProgressState): boolean {
  return JSON.stringify({ ...a, updatedAt: 0 }) === JSON.stringify({ ...b, updatedAt: 0 });
}
