/**
 * Learner progress, persisted in the browser.
 *
 * Everything the learner does is recorded here: per-item spaced-repetition
 * state, lesson results, finished-session summaries and the session in
 * progress (so it can be resumed after a reload). The store survives broken
 * or unavailable storage by falling back to memory and saying so.
 */
import type { PracticeMode, Question } from "./quiz";
import { review, type ItemProgress } from "./srs";
import { bump, type Activity } from "./streak";

export const STORAGE_KEY = "unit24.progress";
export const STATE_VERSION = 1;
const MAX_HISTORY = 30;

export interface LessonResult {
  completedAt: number | null;
  bestScore: number;
  total: number;
  attempts: number;
}

export interface AnswerRecord {
  questionId: string;
  response: string;
  correct: boolean;
  /** Per item, whether it was answered correctly (a spelling question covers several letters). */
  itemResults: Record<string, boolean>;
  at: number;
  /** Items that reached the top box with this answer. */
  mastered: string[];
}

export interface ActiveSession {
  id: string;
  mode: PracticeMode;
  startedAt: number;
  questions: Question[];
  answers: AnswerRecord[];
  /** Index of the question on screen. It moves on only when the learner leaves the feedback. */
  cursor: number;
}

export interface SessionSummary {
  id: string;
  mode: PracticeMode;
  startedAt: number;
  finishedAt: number;
  total: number;
  correct: number;
  missedItemIds: string[];
  masteredItemIds: string[];
}

export interface ProgressState {
  version: typeof STATE_VERSION;
  items: Record<string, ItemProgress>;
  lessons: Record<string, LessonResult>;
  sessions: SessionSummary[];
  activeSession: ActiveSession | null;
  /** Answers given per local day, for streaks and the daily count. */
  activity: Activity;
  /** When this state last changed (ms), used to merge with a synced copy. */
  updatedAt: number;
}

export type StorageNotice = "unavailable" | "corrupt" | "write-failed" | null;

export function emptyState(): ProgressState {
  return { version: STATE_VERSION, items: {}, lessons: {}, sessions: [], activeSession: null, activity: {}, updatedAt: 0 };
}

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

function validItem(v: unknown): v is ItemProgress {
  return (
    isObj(v) &&
    isNum(v.box) &&
    v.box >= 1 &&
    v.box <= 5 &&
    isNum(v.seen) &&
    isNum(v.correct) &&
    isNum(v.lastSeenAt) &&
    isNum(v.dueAt) &&
    (v.lastResult === "correct" || v.lastResult === "wrong")
  );
}

function validSession(v: unknown): v is ActiveSession {
  return (
    isObj(v) &&
    typeof v.id === "string" &&
    typeof v.mode === "string" &&
    Array.isArray(v.questions) &&
    v.questions.length > 0 &&
    Array.isArray(v.answers) &&
    isNum(v.cursor) &&
    v.cursor >= 0 &&
    v.cursor < v.questions.length
  );
}

/** Parses stored or imported progress. Throws with a readable message if it is not progress data. */
export function parseState(text: string): ProgressState {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("The progress data is not valid JSON.");
  }
  if (!isObj(data) || data.version !== STATE_VERSION) throw new Error("This is not Unit-24 progress data (unknown version).");
  if (!isObj(data.items) || !isObj(data.lessons) || !Array.isArray(data.sessions)) throw new Error("The progress data is incomplete.");
  const items: Record<string, ItemProgress> = {};
  for (const [id, p] of Object.entries(data.items)) if (validItem(p)) items[id] = p;
  const lessons: Record<string, LessonResult> = {};
  for (const [id, l] of Object.entries(data.lessons)) {
    if (isObj(l) && isNum(l.bestScore) && isNum(l.total) && isNum(l.attempts)) {
      lessons[id] = { completedAt: isNum(l.completedAt) ? l.completedAt : null, bestScore: l.bestScore, total: l.total, attempts: l.attempts };
    }
  }
  const sessions = data.sessions.filter(
    (s): s is SessionSummary => isObj(s) && typeof s.id === "string" && isNum(s.total) && isNum(s.correct) && Array.isArray(s.missedItemIds),
  );
  const activeSession = validSession(data.activeSession) ? data.activeSession : null;
  const activity: Activity = {};
  if (isObj(data.activity)) for (const [day, n] of Object.entries(data.activity)) if (/^\d{4}-\d{2}-\d{2}$/.test(day) && isNum(n) && n > 0) activity[day] = n;
  const updatedAt = isNum(data.updatedAt) ? data.updatedAt : 0;
  return { version: STATE_VERSION, items, lessons, sessions: sessions.slice(0, MAX_HISTORY), activeSession, activity, updatedAt };
}

export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

function defaultStorage(): KeyValueStorage | null {
  try {
    const s = window.localStorage;
    const probe = `${STORAGE_KEY}.probe`;
    s.setItem(probe, "1");
    s.removeItem(probe);
    return s;
  } catch {
    return null;
  }
}

export const PASS_RATIO = 0.8;

export class ProgressStore {
  private state: ProgressState;
  private listeners = new Set<() => void>();
  private storage: KeyValueStorage | null;
  notice: StorageNotice = null;

  constructor(storage: KeyValueStorage | null | undefined = undefined) {
    this.storage = storage === undefined ? defaultStorage() : storage;
    this.state = emptyState();
    if (this.storage === null) {
      this.notice = "unavailable";
      return;
    }
    let raw: string | null = null;
    try {
      raw = this.storage.getItem(STORAGE_KEY);
    } catch {
      this.notice = "unavailable";
      this.storage = null;
      return;
    }
    if (raw !== null) {
      try {
        this.state = parseState(raw);
      } catch {
        this.notice = "corrupt";
        try {
          this.storage.setItem(`${STORAGE_KEY}.corrupt-backup`, raw);
        } catch {
          /* best effort: keep the unreadable copy for inspection */
        }
      }
    }
  }

  getState = (): ProgressState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  dismissNotice(): void {
    if (this.notice === "corrupt") this.notice = null;
    this.emit();
  }

  private set(next: ProgressState): void {
    this.state = { ...next, updatedAt: Date.now() };
    if (this.storage) {
      try {
        this.storage.setItem(STORAGE_KEY, JSON.stringify(this.state));
        if (this.notice === "write-failed") this.notice = null;
      } catch {
        this.notice = "write-failed";
      }
    }
    this.emit();
  }

  private emit(): void {
    for (const l of this.listeners) l();
  }

  /** Applies spaced-repetition results. Returns ids that reached the top box with this answer. */
  recordResults(results: Record<string, boolean>, now: number): string[] {
    const items = { ...this.state.items };
    const mastered: string[] = [];
    for (const [id, ok] of Object.entries(results)) {
      const before = items[id];
      const after = review(before, ok, now);
      items[id] = after;
      if (after.box === 5 && (before?.box ?? 0) < 5) mastered.push(id);
    }
    this.set({ ...this.state, items, activity: bump(this.state.activity, now) });
    return mastered;
  }

  recordLessonCheck(lessonId: string, score: number, total: number, now: number): LessonResult {
    const prev = this.state.lessons[lessonId];
    const passed = total > 0 && score / total >= PASS_RATIO;
    const result: LessonResult = {
      completedAt: prev?.completedAt ?? (passed ? now : null),
      bestScore: Math.max(prev?.bestScore ?? 0, score),
      total,
      attempts: (prev?.attempts ?? 0) + 1,
    };
    this.set({ ...this.state, lessons: { ...this.state.lessons, [lessonId]: result } });
    return result;
  }

  startSession(session: ActiveSession): void {
    this.set({ ...this.state, activeSession: session });
  }

  /** Records an answer to the current question and updates item scheduling. */
  answer(record: Omit<AnswerRecord, "mastered">): AnswerRecord {
    const s = this.state.activeSession;
    if (!s) throw new Error("No session in progress");
    const existing = s.answers.find((a) => a.questionId === record.questionId);
    if (existing) return existing;
    const stored: AnswerRecord = { ...record, mastered: this.recordResults(record.itemResults, record.at) };
    const active = this.state.activeSession!;
    this.set({ ...this.state, activeSession: { ...active, answers: [...active.answers, stored] } });
    return stored;
  }

  /** Finishes the session in progress and stores its summary. */
  finishSession(now: number): SessionSummary | null {
    const s = this.state.activeSession;
    if (!s) return null;
    const missed = new Set<string>();
    for (const a of s.answers) for (const [id, ok] of Object.entries(a.itemResults)) if (!ok) missed.add(id);
    const summary: SessionSummary = {
      id: s.id,
      mode: s.mode,
      startedAt: s.startedAt,
      finishedAt: now,
      total: s.answers.length,
      correct: s.answers.filter((a) => a.correct).length,
      missedItemIds: [...missed],
      masteredItemIds: [...new Set(s.answers.flatMap((a) => a.mastered ?? []))],
    };
    this.set({ ...this.state, activeSession: null, sessions: [summary, ...this.state.sessions].slice(0, MAX_HISTORY) });
    return summary;
  }

  /** Moves past the current question once it has been answered. */
  advance(): void {
    const s = this.state.activeSession;
    if (!s) return;
    const current = s.questions[s.cursor];
    if (!current || !s.answers.some((a) => a.questionId === current.id)) return;
    if (s.cursor + 1 >= s.questions.length) return;
    this.set({ ...this.state, activeSession: { ...s, cursor: s.cursor + 1 } });
  }

  abandonSession(): void {
    this.set({ ...this.state, activeSession: null });
  }

  reset(): void {
    this.set(emptyState());
  }

  exportJson(): string {
    return JSON.stringify(this.state, null, 2);
  }

  /** Replaces the whole state (used when merging a synced copy). Validated like any import. */
  replace(next: ProgressState): void {
    this.set(parseState(JSON.stringify(next)));
  }

  importJson(text: string): void {
    this.set(parseState(text));
  }
}
