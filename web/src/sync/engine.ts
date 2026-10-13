import type { ProgressState, ProgressStore } from "../lib/progress";
import { mergeProgress, sameProgress } from "./merge";

export interface SyncBackend {
  pull(uid: string): Promise<ProgressState | null>;
  push(uid: string, state: ProgressState): Promise<void>;
}

export type SyncStatus = "off" | "syncing" | "synced" | "error" | "offline";

export interface SyncSnapshot {
  status: SyncStatus;
  lastSyncedAt: number | null;
  error: string | null;
}

/**
 * Keeps the device's progress and the account copy in step: on sign-in and when the app comes back
 * to the foreground it pulls and merges; after local changes it pushes, debounced.
 */
export class SyncEngine {
  private uid: string | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private unsubscribe: (() => void) | null = null;
  private applying = false;
  private snapshot: SyncSnapshot = { status: "off", lastSyncedAt: null, error: null };
  private listeners = new Set<() => void>();

  constructor(
    private store: ProgressStore,
    private backend: SyncBackend,
    private debounceMs = 2500,
    private now: () => number = Date.now,
  ) {}

  getSnapshot = (): SyncSnapshot => this.snapshot;

  subscribe = (l: () => void): (() => void) => {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  };

  private setSnapshot(next: Partial<SyncSnapshot>) {
    this.snapshot = { ...this.snapshot, ...next };
    this.listeners.forEach((l) => l());
  }

  private fail(e: unknown) {
    const offline = typeof navigator !== "undefined" && navigator.onLine === false;
    this.setSnapshot({ status: offline ? "offline" : "error", error: e instanceof Error ? e.message : String(e) });
  }

  async start(uid: string): Promise<void> {
    this.stop();
    this.uid = uid;
    this.unsubscribe = this.store.subscribe(() => {
      if (!this.applying) this.schedule();
    });
    await this.syncNow();
  }

  stop(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.uid = null;
    this.setSnapshot({ status: "off", error: null });
  }

  /** Pull, merge into the device, then push the merged copy. */
  async syncNow(): Promise<void> {
    const uid = this.uid;
    if (!uid) return;
    this.setSnapshot({ status: "syncing" });
    try {
      const remote = await this.backend.pull(uid);
      if (uid !== this.uid) return;
      const local = this.store.getState();
      const merged = remote ? mergeProgress(local, remote) : local;
      if (!sameProgress(merged, local)) {
        this.applying = true;
        try {
          this.store.replace(merged);
        } finally {
          this.applying = false;
        }
      }
      if (!remote || !sameProgress(merged, remote)) await this.backend.push(uid, this.store.getState());
      this.setSnapshot({ status: "synced", lastSyncedAt: this.now(), error: null });
    } catch (e) {
      this.fail(e);
    }
  }

  private schedule() {
    if (!this.uid) return;
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => void this.flush(), this.debounceMs);
  }

  /** Pushes pending local changes now (e.g. when the app goes to the background). */
  async flush(): Promise<void> {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const uid = this.uid;
    if (!uid) return;
    this.setSnapshot({ status: "syncing" });
    try {
      await this.backend.push(uid, this.store.getState());
      this.setSnapshot({ status: "synced", lastSyncedAt: this.now(), error: null });
    } catch (e) {
      this.fail(e);
    }
  }

  hasPending(): boolean {
    return this.timer !== null;
  }
}
