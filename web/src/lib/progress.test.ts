import { type KeyValueStorage, ProgressStore, STORAGE_KEY, emptyState, parseState } from "./progress";
import type { Question } from "./quiz";

class MemoryStorage implements KeyValueStorage {
  data = new Map<string, string>();
  failWrites = false;
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    if (this.failWrites) throw new Error("quota");
    this.data.set(k, v);
  }
  removeItem(k: string) {
    this.data.delete(k);
  }
}

const NOW = Date.UTC(2026, 9, 1);
const q: Question = { id: "q1", type: "code-to-meaning", itemIds: ["a"], subject: "10-1", options: ["x", "y"], answer: "x" };

describe("ProgressStore", () => {
  it("persists and reloads item progress", () => {
    const storage = new MemoryStorage();
    const s = new ProgressStore(storage);
    s.recordResults({ a: true, b: false }, NOW);
    const again = new ProgressStore(storage);
    expect(again.getState().items.a?.box).toBe(2);
    expect(again.getState().items.b?.box).toBe(1);
    expect(again.notice).toBeNull();
  });

  it("resumes an active session after reload and summarizes it", () => {
    const storage = new MemoryStorage();
    const s = new ProgressStore(storage);
    s.startSession({ id: "s1", mode: "mixed", startedAt: NOW, questions: [q, { ...q, id: "q2", itemIds: ["b"] }], answers: [], cursor: 0 });
    s.answer({ questionId: "q1", response: "y", correct: false, itemResults: { a: false }, at: NOW });
    s.answer({ questionId: "q1", response: "x", correct: true, itemResults: { a: true }, at: NOW });
    let resumed = new ProgressStore(storage);
    expect(resumed.getState().activeSession).toMatchObject({ cursor: 0, answers: [{ questionId: "q1", correct: false }] });
    resumed.advance();
    resumed.advance();
    resumed = new ProgressStore(storage);
    expect(resumed.getState().activeSession?.cursor).toBe(1);
    resumed.answer({ questionId: "q2", response: "x", correct: true, itemResults: { b: true }, at: NOW });
    const summary = resumed.finishSession(NOW + 1);
    expect(summary).toMatchObject({ total: 2, correct: 1, missedItemIds: ["a"] });
    expect(resumed.getState().activeSession).toBeNull();
    expect(new ProgressStore(storage).getState().sessions).toHaveLength(1);
  });

  it("records lesson completion only when the check is passed", () => {
    const s = new ProgressStore(new MemoryStorage());
    expect(s.recordLessonCheck("l1", 3, 5, NOW).completedAt).toBeNull();
    const r = s.recordLessonCheck("l1", 4, 5, NOW + 1);
    expect(r).toMatchObject({ completedAt: NOW + 1, bestScore: 4, attempts: 2 });
    expect(s.recordLessonCheck("l1", 1, 5, NOW + 2).completedAt).toBe(NOW + 1);
  });

  it("recovers from corrupt storage, keeps a backup and reports it", () => {
    const storage = new MemoryStorage();
    storage.setItem(STORAGE_KEY, "{not json");
    const s = new ProgressStore(storage);
    expect(s.notice).toBe("corrupt");
    expect(s.getState()).toEqual(emptyState());
    expect(storage.getItem(`${STORAGE_KEY}.corrupt-backup`)).toBe("{not json");
  });

  it("works in memory when storage is unavailable or writes fail", () => {
    const s = new ProgressStore(null);
    expect(s.notice).toBe("unavailable");
    s.recordResults({ a: true }, NOW);
    expect(s.getState().items.a).toBeDefined();

    const storage = new MemoryStorage();
    const w = new ProgressStore(storage);
    storage.failWrites = true;
    w.recordResults({ a: true }, NOW);
    expect(w.notice).toBe("write-failed");
    expect(w.getState().items.a).toBeDefined();
  });

  it("exports, imports and resets", () => {
    const s = new ProgressStore(new MemoryStorage());
    s.recordResults({ a: true }, NOW);
    const json = s.exportJson();
    s.reset();
    expect(s.getState().items).toEqual({});
    s.importJson(json);
    expect(s.getState().items.a?.box).toBe(2);
    expect(() => s.importJson('{"version":99}')).toThrow(/unknown version/);
    expect(() => s.importJson("nope")).toThrow(/not valid JSON/);
  });

  it("notifies subscribers", () => {
    const s = new ProgressStore(new MemoryStorage());
    const fn = vi.fn();
    const off = s.subscribe(fn);
    s.recordResults({ a: true }, NOW);
    off();
    s.recordResults({ a: true }, NOW);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("parseState", () => {
  it("rejects malformed records instead of silently discarding them", () => {
    expect(() => parseState(JSON.stringify({ ...emptyState(), items: { a: { box: 9 } } }))).toThrow(/invalid/);
  });
});
