import { emptyState, type ProgressState } from "../lib/progress";
import type { ItemProgress } from "../lib/srs";
import { mergeProgress, sameProgress } from "./merge";

const item = (lastSeenAt: number, box: number, seen = 1): ItemProgress => ({ box, seen, correct: seen, lastResult: "correct", lastSeenAt, dueAt: lastSeenAt });
const state = (over: Partial<ProgressState>): ProgressState => ({ ...emptyState(), ...over });

describe("mergeProgress", () => {
  it("keeps the most recent answer for each item and the union of items", () => {
    const local = state({ items: { a: item(100, 2), b: item(50, 3) } });
    const remote = state({ items: { a: item(200, 1), c: item(10, 4) } });
    const m = mergeProgress(local, remote);
    expect(m.items.a!.box).toBe(1);
    expect(m.items.b!.box).toBe(3);
    expect(m.items.c!.box).toBe(4);
  });

  it("keeps the best lesson result and the earliest completion", () => {
    const local = state({ lessons: { l: { completedAt: null, bestScore: 3, total: 5, attempts: 2 } } });
    const remote = state({ lessons: { l: { completedAt: 500, bestScore: 5, total: 5, attempts: 1 } } });
    expect(mergeProgress(local, remote).lessons.l).toEqual({ completedAt: 500, bestScore: 5, total: 5, attempts: 2 });
  });

  it("unions session history and drops an active session that the other device finished", () => {
    const summary = { id: "s1", mode: "mixed" as const, startedAt: 1, finishedAt: 10, total: 1, correct: 1, missedItemIds: [], masteredItemIds: [] };
    const active = { id: "s1", mode: "mixed" as const, startedAt: 1, questions: [{ id: "q1", type: "spell" as const, itemIds: ["a"], subject: "A", answerWords: ["Adam"], answer: "Adam" }], answers: [], cursor: 0 };
    const local = state({ activeSession: active });
    const remote = state({ sessions: [summary] });
    const m = mergeProgress(local, remote);
    expect(m.sessions.map((s) => s.id)).toEqual(["s1"]);
    expect(m.activeSession).toBeNull();
  });

  it("keeps the larger daily activity count", () => {
    const m = mergeProgress(state({ activity: { "2026-10-12": 3 } }), state({ activity: { "2026-10-12": 5, "2026-10-13": 1 } }));
    expect(m.activity).toEqual({ "2026-10-12": 5, "2026-10-13": 1 });
  });

  it("discards malformed remote data instead of importing it", () => {
    const remote = { ...emptyState(), items: { bad: { box: 99 } } } as unknown as ProgressState;
    expect(mergeProgress(emptyState(), remote).items).toEqual({});
  });

  it("compares states ignoring the change time", () => {
    expect(sameProgress(state({ updatedAt: 1 }), state({ updatedAt: 2 }))).toBe(true);
    expect(sameProgress(state({ items: { a: item(1, 1) } }), state({}))).toBe(false);
  });
});
