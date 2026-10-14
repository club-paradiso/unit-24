import { emptyState, parseState, ProgressStore, STORAGE_KEY, type KeyValueStorage } from './progress';
import { review, DAY_MS } from './srs';
import type { Question } from './quiz';

class Mem implements KeyValueStorage {
  data = new Map<string, string>();
  writes: string[] = [];
  getItem(k: string) { return this.data.get(k) ?? null; }
  setItem(k: string, v: string) { this.data.set(k, v); if (k === STORAGE_KEY) this.writes.push(v); }
  removeItem(k: string) { this.data.delete(k); }
}
const q: Question = { id: 'q1', type: 'code-to-meaning', itemIds: ['a'], subject: '10-1', answer: 'poor', options: ['poor', 'good'] };

describe('recovery: data integrity', () => {
  it.each([
    { activeSession: { id: 's', mode: 'mixed', startedAt: 1, questions: [null], answers: [], cursor: 0 } },
    { sessions: [{ id: 's', total: 1, correct: 3, missedItemIds: [] }] },
    { items: { a: { box: 1.5, seen: -1, correct: 9, lastSeenAt: 0, dueAt: 0, lastResult: 'correct' } } },
    { activity: { '2026-02-31': 1 } },
  ])('rejects invalid nested data without replacing valid progress: %j', (bad) => {
    const s = new ProgressStore(new Mem()); s.recordResults({ kept: true }, 1);
    const before = s.exportJson();
    expect(() => s.importJson(JSON.stringify({ ...emptyState(), ...bad }))).toThrow();
    expect(s.exportJson()).toBe(before);
  });
  it('rejects a contradictory answer in a restored session', () => {
    const activeSession = { id: 's', mode: 'mixed', startedAt: 1, questions: [q], cursor: 0,
      answers: [{ questionId: q.id, response: 'good', correct: true, itemResults: { a: true }, mastered: [], at: 2 }] };
    expect(() => parseState(JSON.stringify({ ...emptyState(), activeSession }))).toThrow();
  });
  it('records scheduling and the answer in a single durable write', () => {
    const mem = new Mem(); const s = new ProgressStore(mem);
    s.startSession({ id: 's', mode: 'mixed', startedAt: 1, questions: [q], answers: [], cursor: 0 });
    mem.writes = [];
    s.answer({ questionId: q.id, response: 'poor', correct: true, itemResults: { a: true }, at: 2 });
    expect(mem.writes).toHaveLength(1);
    expect(new ProgressStore(mem).getState().activeSession?.answers).toHaveLength(1);
  });
  it('preserves edits from two already-open tabs', () => {
    const mem = new Mem(); const a = new ProgressStore(mem); const b = new ProgressStore(mem);
    a.recordResults({ a: true }, 1); b.recordResults({ b: false }, 2); a.recordResults({ a: true }, 3);
    const saved = new ProgressStore(mem).getState();
    expect(Object.keys(saved.items).sort()).toEqual(['a', 'b']);
    expect(saved.items.a?.seen).toBe(2);
  });
  it('backs up corruption introduced by another tab before the next write', () => {
    const mem = new Mem(); const store = new ProgressStore(mem);
    store.recordResults({ kept: true }, 1);
    mem.setItem(STORAGE_KEY, '{corrupt');
    store.recordResults({ another: true }, 2);
    expect(mem.getItem(`${STORAGE_KEY}.corrupt-backup`)).toBe('{corrupt');
    expect(store.notice).toBe('corrupt');
    expect(Object.keys(new ProgressStore(mem).getState().items)).toEqual(['kept', 'another']);
  });
  it('does not claim a successful backup or overwrite the original when recovery storage fails', () => {
    const mem = new Mem(); mem.setItem(STORAGE_KEY, '{only-copy');
    const originalSet = mem.setItem.bind(mem);
    mem.setItem = (k, v) => { if (k.endsWith('.corrupt-backup')) throw new Error('quota'); originalSet(k, v); };
    const store = new ProgressStore(mem);
    expect(store.notice).toBe('recovery-failed');
    expect(store.recoveryJson()).toBe('{only-copy');
    store.recordResults({ new: true }, 1);
    expect(mem.getItem(STORAGE_KEY)).toBe('{only-copy');
  });
  it('makes the pre-import progress downloadable without changing current progress', () => {
    const store = new ProgressStore(new Mem()); store.recordResults({ kept: true }, 1);
    const before = store.exportJson();
    store.importJson(JSON.stringify(emptyState()));
    expect(store.recoveryJson()).toBe(before);
    expect(store.getState().items).toEqual({});
  });
  it('does not delay the scheduled review when practising early', () => {
    const first = review(undefined, true, 1000);
    expect(review(first, true, 1000 + DAY_MS / 2).dueAt).toBe(first.dueAt);
  });
});
