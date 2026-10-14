/**
 * Learner progress, persisted in the browser.
 *
 * Everything the learner does is recorded here: per-item spaced-repetition
 * state, lesson results, finished-session summaries and the session in
 * progress (so it can be resumed after a reload). The store survives broken
 * or unavailable storage by falling back to memory and saying so.
 */
import { isCorrect, spellBreakdown, type PracticeMode, type Question } from "./quiz";
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

export interface LessonDraft {
  phase: "study" | "check" | "done";
  index: number;
  questions: Question[];
  answers: AnswerRecord[];
  contentVersion: string;
  updatedAt: number;
}

export interface ProgressState {
  version: typeof STATE_VERSION;
  items: Record<string, ItemProgress>;
  lessons: Record<string, LessonResult>;
  sessions: SessionSummary[];
  activeSession: ActiveSession | null;
  lessonDrafts: Record<string, LessonDraft>;
  /** Answers given per local day, for streaks and the daily count. */
  activity: Activity;
  /** When this state last changed (ms), used to merge with a synced copy. */
  updatedAt: number;
}

export type StorageNotice = "unavailable" | "corrupt" | "write-failed" | "recovery-failed" | null;

export function emptyState(): ProgressState {
  return { version: STATE_VERSION, items: {}, lessons: {}, sessions: [], activeSession: null, lessonDrafts: {}, activity: {}, updatedAt: 0 };
}

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const count = (v: unknown): v is number => isNum(v) && Number.isSafeInteger(v) && v >= 0;
const timestamp = (v: unknown): v is number => count(v) && v <= 8.64e15;
const str = (v: unknown): v is string => typeof v === "string" && v.length > 0 && v.length <= 10000;
const key = (v: string) => !["__proto__", "constructor", "prototype"].includes(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(str);
const mode = (v: unknown): v is PracticeMode => ["mixed", "codes", "alphabet", "mistakes", "due"].includes(String(v));
const fail = (): never => { throw new Error("The progress data contains invalid or inconsistent records."); };

function validItem(v: unknown): v is ItemProgress {
  return isObj(v) && count(v.box) && v.box >= 1 && v.box <= 5 && count(v.seen) && count(v.correct)
    && v.correct <= v.seen && timestamp(v.lastSeenAt) && timestamp(v.dueAt)
    && (v.lastResult === "correct" || v.lastResult === "wrong");
}

export function validQuestion(v: unknown): v is Question {
  if (!isObj(v) || !str(v.id) || !str(v.subject) || !str(v.answer) || !strings(v.itemIds) || !v.itemIds.length || !v.itemIds.every(key)) return false;
  if (v.type === "spell") return strings(v.answerWords) && v.answerWords.length === v.itemIds.length && v.answerWords.join(" ") === v.answer;
  return ["code-to-meaning", "meaning-to-code", "letter-to-word"].includes(String(v.type))
    && v.itemIds.length === 1 && strings(v.options) && v.options.length >= 1
    && new Set(v.options).size === v.options.length && v.options.includes(v.answer);
}

function validAnswers(answers: unknown, questions: Question[]): answers is AnswerRecord[] {
  if (!Array.isArray(answers) || answers.length > questions.length) return false;
  return answers.every((a, i) => {
    const q = questions[i];
    if (!q || !isObj(a) || a.questionId !== q.id || typeof a.response !== "string" || typeof a.correct !== "boolean"
      || !isObj(a.itemResults) || !timestamp(a.at) || !strings(a.mastered) || !a.mastered.every(id => q.itemIds.includes(id))) return false;
    const expected = q.type === "spell"
      ? Object.fromEntries(q.itemIds.map((id, n) => [id, spellBreakdown(q, a.response as string)[n]!.ok]))
      : { [q.itemIds[0]]: isCorrect(q, a.response) };
    return a.correct === isCorrect(q, a.response) && Object.keys(a.itemResults).length === Object.keys(expected).length
      && Object.entries(expected).every(([id, ok]) => (a.itemResults as Record<string, unknown>)[id] === ok);
  });
}
function validQuestions(v: unknown): v is Question[] {
  return Array.isArray(v) && v.length > 0 && v.length <= 100 && v.every(validQuestion) && new Set(v.map(q => q.id)).size === v.length;
}
function validSession(v: unknown): v is ActiveSession {
  return isObj(v) && str(v.id) && mode(v.mode) && timestamp(v.startedAt) && validQuestions(v.questions)
    && validAnswers(v.answers, v.questions) && count(v.cursor) && v.cursor < v.questions.length
    && v.answers.length >= v.cursor && v.answers.length <= v.cursor + 1;
}
function validLesson(v: unknown): v is LessonResult {
  return isObj(v) && count(v.bestScore) && count(v.total) && v.total > 0 && v.bestScore <= v.total
    && count(v.attempts) && (v.completedAt === null || timestamp(v.completedAt));
}
function validSummary(v: unknown): v is SessionSummary {
  return isObj(v) && str(v.id) && mode(v.mode) && timestamp(v.startedAt) && timestamp(v.finishedAt)
    && count(v.total) && count(v.correct) && v.correct <= v.total && strings(v.missedItemIds) && strings(v.masteredItemIds);
}
function validDraft(v: unknown): v is LessonDraft {
  if (!isObj(v) || !["study", "check", "done"].includes(String(v.phase)) || !count(v.index) || v.index > 100
    || !str(v.contentVersion) || !timestamp(v.updatedAt) || !validQuestions(v.questions) || !validAnswers(v.answers, v.questions)) return false;
  if (v.phase === "study") return v.answers.length === 0;
  if (v.phase === "done") return v.answers.length === v.questions.length;
  return v.index < v.questions.length && v.answers.length >= v.index && v.answers.length <= v.index + 1;
}

/** Reject the entire import on corruption. Never silently drop a learner's records. v1 optional fields migrate additively. */
export function parseState(text: string): ProgressState {
  if (text.length > 400000) throw new Error("The progress file is too large (maximum 400 KB).");
  let data: unknown;
  try { data = JSON.parse(text); } catch { throw new Error("The progress data is not valid JSON."); }
  if (!isObj(data) || data.version !== STATE_VERSION) throw new Error("This is not Unit-24 progress data (unknown version).");
  if (!isObj(data.items) || !isObj(data.lessons) || !Array.isArray(data.sessions)) throw new Error("The progress data is incomplete.");
  const readMap = <T,>(v: unknown, check: (x: unknown) => x is T): Record<string, T> => {
    if (!isObj(v)) return fail();
    const out: Record<string, T> = {};
    for (const [id, value] of Object.entries(v)) {
      if (!key(id) || !check(value)) return fail();
      out[id] = value;
    }
    return out;
  };
  const items = readMap(data.items, validItem);
  const lessons = readMap(data.lessons, validLesson);
  if (!data.sessions.every(validSummary)) return fail();
  const sessions = [...new Map(data.sessions.map(s => [s.id, s])).values()].slice(0, MAX_HISTORY);
  const activeSession = data.activeSession ?? null;
  if (activeSession !== null && !validSession(activeSession)) return fail();
  const lessonDrafts = readMap(data.lessonDrafts ?? {}, validDraft);
  const activity: Activity = {};
  if (data.activity !== undefined) {
    if (!isObj(data.activity)) return fail();
    for (const [day, n] of Object.entries(data.activity)) {
      const d = new Date(day + "T12:00:00Z");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(d.getTime()) || d.toISOString().slice(0,10) !== day || !count(n) || n === 0) return fail();
      activity[day] = n;
    }
  }
  const updatedAt = data.updatedAt ?? 0;
  if (!timestamp(updatedAt)) return fail();
  return { version: STATE_VERSION, items, lessons, sessions, activeSession, lessonDrafts, activity, updatedAt };
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
  private recoveryRaw: string | null = null;
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
        this.recoveryRaw = raw;
        try {
          this.storage.setItem(`${STORAGE_KEY}.corrupt-backup`, raw);
        } catch {
          this.storage = null; // Do not overwrite the only recoverable copy.
          this.notice = "recovery-failed";
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

  /** Read before each mutation so another tab's completed write cannot be overwritten by stale state. */
  refresh = (): void => {
    if (!this.storage || this.notice === "write-failed") return;
    let raw: string | null;
    try { raw = this.storage.getItem(STORAGE_KEY); }
    catch { this.notice = "unavailable"; this.storage = null; this.emit(); return; }
    if (!raw || raw === JSON.stringify(this.state)) return;
    try { this.state = parseState(raw); }
    catch {
      this.notice = "corrupt";
      this.recoveryRaw = raw;
      try { this.storage.setItem(`${STORAGE_KEY}.corrupt-backup`, raw); }
      catch { this.storage = null; this.notice = "recovery-failed"; } // Preserve the only copy if recovery storage fails.
    }
    this.emit();
  };

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
  private applyResults(results: Record<string, boolean>, now: number): { items: ProgressState["items"]; mastered: string[] } {
    const items = { ...this.state.items };
    const mastered: string[] = [];
    for (const [id, ok] of Object.entries(results)) {
      const before = items[id];
      const after = review(before, ok, now);
      items[id] = after;
      if (after.box === 5 && (before?.box ?? 0) < 5) mastered.push(id);
    }
    return { items, mastered };
  }

  recordResults(results: Record<string, boolean>, now: number): string[] {
    this.refresh();
    const { items, mastered } = this.applyResults(results, now);
    this.set({ ...this.state, items, activity: bump(this.state.activity, now) });
    return mastered;
  }

  recordLessonCheck(lessonId: string, score: number, total: number, now: number): LessonResult {
    this.refresh();
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
    this.refresh();
    if (!validSession(session)) throw new Error("Invalid session");
    this.set({ ...this.state, activeSession: session });
  }

  /** Records an answer to the current question and updates item scheduling. */
  answer(record: Omit<AnswerRecord, "mastered">): AnswerRecord {
    this.refresh();
    const s = this.state.activeSession;
    if (!s) throw new Error("No session in progress");
    const existing = s.answers.find((a) => a.questionId === record.questionId);
    if (existing) return existing;
    if (s.questions[s.cursor]?.id !== record.questionId) throw new Error("Answer does not match the current question");
    const { items, mastered } = this.applyResults(record.itemResults, record.at);
    const stored: AnswerRecord = { ...record, mastered };
    if (!validAnswers([...s.answers, stored], s.questions)) throw new Error("Invalid answer");
    this.set({ ...this.state, items, activity: bump(this.state.activity, record.at), activeSession: { ...s, answers: [...s.answers, stored] } });
    return stored;
  }

  /** Finishes the session in progress and stores its summary. */
  finishSession(now: number): SessionSummary | null {
    this.refresh();
    const s = this.state.activeSession;
    if (!s || s.answers.length !== s.questions.length) return null;
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
    this.refresh();
    const s = this.state.activeSession;
    if (!s) return;
    const current = s.questions[s.cursor];
    if (!current || !s.answers.some((a) => a.questionId === current.id)) return;
    if (s.cursor + 1 >= s.questions.length) return;
    this.set({ ...this.state, activeSession: { ...s, cursor: s.cursor + 1 } });
  }

  abandonSession(): void {
    this.refresh();
    this.set({ ...this.state, activeSession: null });
  }

  saveLessonDraft(id: string, draft: LessonDraft): void {
    this.refresh();
    if (!key(id) || !validDraft(draft)) throw new Error("Invalid lesson draft");
    this.set({ ...this.state, lessonDrafts: { ...this.state.lessonDrafts, [id]: draft } });
  }

  answerLesson(id: string, record: Omit<AnswerRecord, "mastered">): void {
    this.refresh();
    const d = this.state.lessonDrafts[id];
    if (!d || d.phase !== "check" || d.answers.some(a => a.questionId === record.questionId)) return;
    if (d.questions[d.index]?.id !== record.questionId) return;
    const { items, mastered } = this.applyResults(record.itemResults, record.at);
    const next = { ...d, answers: [...d.answers, { ...record, mastered }], updatedAt: record.at };
    if (!validDraft(next)) throw new Error("Invalid lesson answer");
    this.set({ ...this.state, items, activity: bump(this.state.activity, record.at), lessonDrafts: { ...this.state.lessonDrafts, [id]: next } });
  }

  completeLesson(id: string, now: number): void {
    this.refresh();
    const d = this.state.lessonDrafts[id];
    if (!d || d.phase !== "check" || d.answers.length !== d.questions.length) return;
    const score = d.answers.filter(a => a.correct).length;
    const prev = this.state.lessons[id];
    const result: LessonResult = { completedAt: prev?.completedAt ?? (score / d.questions.length >= PASS_RATIO ? now : null),
      bestScore: Math.max(prev?.bestScore ?? 0, score), total: d.questions.length, attempts: (prev?.attempts ?? 0) + 1 };
    this.set({ ...this.state, lessons: { ...this.state.lessons, [id]: result },
      lessonDrafts: { ...this.state.lessonDrafts, [id]: { ...d, phase: "done", updatedAt: now } } });
  }

  reset(): void {
    this.set(emptyState());
  }

  /** Downloadable recovery copy, including unreadable originals retained in memory. */
  recoveryJson(): string | null {
    if (this.recoveryRaw !== null) return this.recoveryRaw;
    try { return this.storage?.getItem(`${STORAGE_KEY}.before-import`) ?? this.storage?.getItem(`${STORAGE_KEY}.corrupt-backup`) ?? null; }
    catch { return null; }
  }

  exportJson(): string {
    return JSON.stringify(this.state, null, 2);
  }

  /** Replaces the whole state (used when merging a synced copy). Validated like any import. */
  replace(next: ProgressState): void {
    this.set(parseState(JSON.stringify(next)));
  }

  importJson(text: string): void {
    const next = parseState(text);
    const backup = this.exportJson();
    if (this.storage) this.storage.setItem(`${STORAGE_KEY}.before-import`, backup);
    this.recoveryRaw = backup;
    this.set(next);
  }
}
