import { ProgressStore, type KeyValueStorage, type ProgressState } from "../lib/progress";
import { SyncEngine, type SyncBackend } from "./engine";

class Mem implements KeyValueStorage {
  m = new Map<string, string>();
  getItem(k: string) {
    return this.m.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.m.set(k, v);
  }
  removeItem(k: string) {
    this.m.delete(k);
  }
}

class FakeBackend implements SyncBackend {
  docs = new Map<string, ProgressState>();
  pushes = 0;
  failNext = false;
  async pull(uid: string) {
    if (this.failNext) {
      this.failNext = false;
      throw new Error("network down");
    }
    const d = this.docs.get(uid);
    return d ? structuredClone(d) : null;
  }
  async push(uid: string, s: ProgressState) {
    this.pushes += 1;
    this.docs.set(uid, structuredClone(s));
  }
}

const NOW = Date.UTC(2026, 9, 13);

describe("SyncEngine", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("uploads local progress on first sign-in and merges another device's progress", async () => {
    const backend = new FakeBackend();
    const phone = new ProgressStore(new Mem());
    phone.recordResults({ a: true }, NOW);
    const e1 = new SyncEngine(phone, backend, 1000);
    await e1.start("u1");
    expect(backend.docs.get("u1")!.items.a).toBeDefined();
    expect(e1.getSnapshot().status).toBe("synced");

    const laptop = new ProgressStore(new Mem());
    laptop.recordResults({ b: false }, NOW + 1000);
    const e2 = new SyncEngine(laptop, backend, 1000);
    await e2.start("u1");
    expect(Object.keys(laptop.getState().items).sort()).toEqual(["a", "b"]);
    expect(Object.keys(backend.docs.get("u1")!.items).sort()).toEqual(["a", "b"]);
  });

  it("pushes local changes after a quiet period, once", async () => {
    const backend = new FakeBackend();
    const store = new ProgressStore(new Mem());
    const e = new SyncEngine(store, backend, 1000);
    await e.start("u1");
    const before = backend.pushes;
    store.recordResults({ a: true }, NOW);
    store.recordResults({ b: true }, NOW);
    expect(e.hasPending()).toBe(true);
    await vi.advanceTimersByTimeAsync(1000);
    expect(backend.pushes).toBe(before + 1);
    expect(Object.keys(backend.docs.get("u1")!.items).sort()).toEqual(["a", "b"]);
  });

  it("reports errors and stops cleanly on sign-out", async () => {
    const backend = new FakeBackend();
    backend.failNext = true;
    const store = new ProgressStore(new Mem());
    const e = new SyncEngine(store, backend, 1000);
    await e.start("u1");
    expect(e.getSnapshot()).toMatchObject({ status: "error", error: "network down" });
    e.stop();
    store.recordResults({ a: true }, NOW);
    expect(e.hasPending()).toBe(false);
    expect(e.getSnapshot().status).toBe("off");
  });
});

it("does not resurrect synced status after sign-out during a push", async () => {
  let release!: () => void;
  const backend: SyncBackend = { pull: async () => null, push: () => new Promise<void>(r => { release = r; }) };
  const e = new SyncEngine(new ProgressStore(new Mem()), backend);
  const started = e.start('u1');
  await Promise.resolve();
  e.stop(); release(); await started;
  expect(e.getSnapshot().status).toBe('off');
});

it("pulls remote work before a debounced upload instead of overwriting it", async () => {
  const backend = new FakeBackend(), local = new ProgressStore(new Mem());
  const e = new SyncEngine(local, backend);
  await e.start('u');
  const other = new ProgressStore(new Mem()); other.recordResults({ remote: true }, 10);
  backend.docs.set('u', other.getState());
  local.recordResults({ local: true }, 20);
  await e.flush();
  expect(Object.keys(backend.docs.get('u')!.items).sort()).toEqual(['local', 'remote']);
  e.stop();
});
