/**
 * Leitner spaced repetition.
 *
 * Box 1 is "learning" and is due immediately. A correct answer on a due item
 * moves it up one box; a wrong answer always sends it back to box 1. Answering
 * an item correctly before it is due is recorded but does not promote it, so
 * the top box can only be reached by recalling the item across several days.
 */

export const DAY_MS = 24 * 60 * 60 * 1000;
export const MAX_BOX = 5;
/** Days until next review after landing in box n (index 0 = box 1). */
export const INTERVAL_DAYS = [0, 1, 3, 7, 16] as const;

export interface ItemProgress {
  box: number;
  seen: number;
  correct: number;
  lastResult: "correct" | "wrong";
  lastSeenAt: number;
  dueAt: number;
}

export type ItemState = "new" | "learning" | "reviewing" | "mastered";

export function intervalFor(box: number): number {
  const clamped = Math.min(Math.max(box, 1), MAX_BOX);
  return INTERVAL_DAYS[clamped - 1]! * DAY_MS;
}

export function isDue(p: ItemProgress | undefined, now: number): boolean {
  return p !== undefined && p.dueAt <= now;
}

export function review(prev: ItemProgress | undefined, correct: boolean, now: number): ItemProgress {
  let box: number;
  if (!correct) box = 1;
  else if (prev === undefined) box = 2;
  else if (prev.dueAt <= now) box = Math.min(prev.box + 1, MAX_BOX);
  else box = prev.box;
  return {
    box,
    seen: (prev?.seen ?? 0) + 1,
    correct: (prev?.correct ?? 0) + (correct ? 1 : 0),
    lastResult: correct ? "correct" : "wrong",
    lastSeenAt: now,
    dueAt: correct && prev && prev.dueAt > now ? prev.dueAt : now + intervalFor(box),
  };
}

export function stateOf(p: ItemProgress | undefined): ItemState {
  if (p === undefined) return "new";
  if (p.box >= MAX_BOX) return "mastered";
  if (p.box >= 3) return "reviewing";
  return "learning";
}

/** Items the learner got wrong last time, or that are back in the first box. */
export function needsReview(p: ItemProgress | undefined): boolean {
  return p !== undefined && (p.lastResult === "wrong" || p.box <= 1);
}

