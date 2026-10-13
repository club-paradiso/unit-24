/**
 * Human review records, in exactly the shape `src/radiocorpus/learning/human_review.py`
 * validates (schema "human-review-1"). The reviewer page builds them in the browser; a person
 * commits the downloaded file to data/adjudication/human/chp_reviews.jsonl.
 */
import { content, SYSTEM_LABEL } from "../content";
import type { CodeSystem } from "../content/types";

export const REVIEW_SCHEMA = "human-review-1";
export type Decision = "ACCEPT" | "REJECT" | "CORRECT";

export interface ReviewEntry {
  factId: string;
  term: string;
  typeLabel: string;
  /** The answer learners currently see, or null when the entry is not taught. */
  shownAnswer: string | null;
  excerpt: string;
  page: number | null;
  taught: boolean;
  /** Why it is not taught (excluded entries only). */
  reason: string | null;
}

export interface Draft {
  decision: Decision;
  meaning: string;
  notes: string;
  /** YYYY-MM-DD, the day the reviewer made this decision. */
  decidedOn: string;
}

export interface ReviewRecord {
  schema: typeof REVIEW_SCHEMA;
  fact_id: string;
  document_sha256: string;
  decision: Decision;
  meaning_as_printed: string | null;
  page: number;
  reviewer: string;
  reviewed_at: string;
  notes: string;
}

function typeLabel(system: string | null, kind: string): string {
  if (system && system in SYSTEM_LABEL) return SYSTEM_LABEL[system as CodeSystem];
  return kind === "letter" ? "Alphabet entry" : "Code";
}

/** Every reviewed CHP entry, taught ones first, in the bundle's order. */
export function reviewEntries(): ReviewEntry[] {
  const taught: ReviewEntry[] = content.items.map((i) => ({
    factId: i.id,
    term: i.term,
    typeLabel: SYSTEM_LABEL[i.code_system],
    shownAnswer: i.answer,
    excerpt: i.excerpt,
    page: i.page,
    taught: true,
    reason: null,
  }));
  const excluded: ReviewEntry[] = content.excluded.map((e) => ({
    factId: e.fact_id,
    term: e.term === "APCO_1941" ? "Alphabet label “APCO 1941”" : e.term,
    typeLabel: typeLabel(e.code_system, e.kind),
    shownAnswer: null,
    excerpt: e.excerpt,
    page: e.page,
    taught: false,
    reason: e.reason,
  }));
  return [...taught, ...excluded];
}

const norm = (s: string) => s.split(/\s+/).filter(Boolean).join(" ").toLowerCase();

/** The same rules the Python validator applies, so a reviewer sees problems before committing. */
export function draftProblem(entry: ReviewEntry, draft: Draft): string | null {
  if (draft.decision === "ACCEPT" && !entry.taught) return "This entry is not taught, so there is nothing to accept. Use “Correct” and type the meaning as printed.";
  if (draft.decision === "REJECT" && !draft.notes.trim()) return "Say why it should not be taught.";
  if (draft.decision === "CORRECT") {
    if (!draft.meaning.trim()) return "Type the meaning exactly as printed on the card.";
    if (!norm(entry.excerpt).includes(norm(draft.meaning)) && !draft.notes.trim())
      return "That text is not in the recorded excerpt. Add a note saying where on the card you read it.";
  }
  return null;
}

export function toRecord(entry: ReviewEntry, draft: Draft, reviewer: string): ReviewRecord {
  return {
    schema: REVIEW_SCHEMA,
    fact_id: entry.factId,
    document_sha256: content.source.sha256,
    decision: draft.decision,
    meaning_as_printed: draft.decision === "CORRECT" ? draft.meaning.split(/\s+/).filter(Boolean).join(" ") : null,
    page: entry.page ?? 1,
    reviewer: reviewer.trim(),
    reviewed_at: draft.decidedOn,
    notes: draft.notes.trim(),
  };
}

export function toJsonl(records: ReviewRecord[]): string {
  return records.map((r) => JSON.stringify(r)).join("\n") + (records.length ? "\n" : "");
}

export function today(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/* ---------- reviewer drafts, kept apart from learner progress ---------- */

export const REVIEW_KEY = "unit24.review";

export interface ReviewState {
  version: 1;
  reviewer: string;
  drafts: Record<string, Draft>;
}

export function loadReviewState(): ReviewState {
  try {
    const raw = window.localStorage.getItem(REVIEW_KEY);
    if (raw) {
      const data = JSON.parse(raw) as Partial<ReviewState>;
      if (data.version === 1 && typeof data.reviewer === "string" && data.drafts && typeof data.drafts === "object") {
        return { version: 1, reviewer: data.reviewer, drafts: data.drafts };
      }
    }
  } catch {
    /* unreadable or unavailable: start empty */
  }
  return { version: 1, reviewer: "", drafts: {} };
}

export function saveReviewState(state: ReviewState): boolean {
  try {
    window.localStorage.setItem(REVIEW_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}
