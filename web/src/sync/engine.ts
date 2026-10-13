import type { ProgressState, ProgressStore } from "../lib/progress";
import { mergeProgress, sameProgress } from "./merge";

export interface SyncBackend {
  pull(uid: string): Promise<ProgressState | null>;
  /** Production writes must merge transactionally, returning the committed state. */
  push(uid: string, state: ProgressState): Promise<ProgressState | void>;
}
export type SyncStatus = "off" | "syncing" | "synced" | "error" | "offline";
export interface SyncSnapshot { status: SyncStatus; lastSyncedAt: number | null; error: string | null; }

/** Serializes pull/merge/push and rejects completions from an obsolete auth session. */
export class SyncEngine {
  private uid: string | null = null;
  private epoch = 0;
  private flight: Promise<void> | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private unsubscribe: (() => void) | null = null;
  private applying = false;
  private snapshot: SyncSnapshot = { status: "off", lastSyncedAt: null, error: null };
  private listeners = new Set<() => void>();
  constructor(private store: ProgressStore, private backend: SyncBackend, private debounceMs = 2500, private now: () => number = Date.now) {}
  getSnapshot = (): SyncSnapshot => this.snapshot;
  subscribe = (l: () => void): (() => void) => { this.listeners.add(l); return () => this.listeners.delete(l); };
  private setSnapshot(next: Partial<SyncSnapshot>) { this.snapshot = { ...this.snapshot, ...next }; this.listeners.forEach(l => l()); }
  async start(uid: string): Promise<void> {
    this.stop(); this.uid = uid;
    this.unsubscribe = this.store.subscribe(() => { if (!this.applying) this.schedule(); });
    await this.syncNow();
  }
  stop(): void {
    this.epoch++; this.unsubscribe?.(); this.unsubscribe = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null; this.uid = null; this.flight = null;
    this.setSnapshot({ status: "off", error: null, lastSyncedAt: null });
  }
  syncNow(): Promise<void> {
    if (!this.uid) return Promise.resolve();
    if (this.flight) return this.flight;
    const uid = this.uid, epoch = this.epoch;
    const current = () => this.uid === uid && this.epoch === epoch;
    const apply = (remote: ProgressState) => {
      const local = this.store.getState(), merged = mergeProgress(local, remote);
      if (!sameProgress(local, merged)) {
        this.applying = true;
        try { this.store.replace(merged); } finally { this.applying = false; }
      }
    };
    this.setSnapshot({ status: "syncing", error: null });
    const run = async () => {
      try {
        const remote = await this.backend.pull(uid);
        if (!current()) return;
        if (remote) apply(remote);
        const sent = this.store.getState();
        if (!remote || !sameProgress(sent, remote)) {
          const committed = await this.backend.push(uid, sent);
          if (!current()) return;
          if (committed) apply(committed);
        }
        if (current()) this.setSnapshot({ status: "synced", lastSyncedAt: this.now(), error: null });
      } catch (e) {
        if (current()) this.setSnapshot({ status: typeof navigator !== "undefined" && !navigator.onLine ? "offline" : "error", error: e instanceof Error ? e.message : String(e) });
      } finally { if (current()) this.flight = null; }
    };
    this.flight = run();
    return this.flight;
  }
  private schedule() {
    if (!this.uid) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush(), this.debounceMs);
  }
  async flush(): Promise<void> {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const epoch = this.epoch;
    if (this.flight) await this.flight;
    if (epoch === this.epoch) await this.syncNow();
  }
  hasPending(): boolean { return this.timer !== null; }
}
