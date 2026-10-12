/**
 * Exercise generation. Every question is built only from teachable items in
 * the content bundle; distractors are other teachable answers of the same
 * kind, so a learner never sees an invented meaning.
 */
import type { LearningItem } from "../content/types";
import { isDue, needsReview, type ItemProgress } from "./srs";
import { pick, shuffle, type Rng } from "./random";

export type QuestionType = "code-to-meaning" | "meaning-to-code" | "letter-to-word" | "spell";
export type PracticeMode = "mixed" | "codes" | "alphabet" | "mistakes" | "due";

export interface ChoiceQuestion {
  id: string;
  type: Exclude<QuestionType, "spell">;
  itemIds: [string];
  prompt: string;
  /** The thing being asked about, shown large (a code, a meaning or a letter). */
  subject: string;
  options: string[];
  answer: string;
}

export interface SpellQuestion {
  id: string;
  type: "spell";
  itemIds: string[];
  prompt: string;
  subject: string;
  /** The card words for each letter, in order. */
  answerWords: string[];
  answer: string;
}

export type Question = ChoiceQuestion | SpellQuestion;

export const QUESTION_LABEL: Record<QuestionType, string> = {
  "code-to-meaning": "Code → meaning",
  "meaning-to-code": "Meaning → code",
  "letter-to-word": "Letter → card word",
  spell: "Spell it out",
};

export const MODE_LABEL: Record<PracticeMode, string> = {
  mixed: "Mixed practice",
  codes: "Codes only",
  alphabet: "Card alphabet only",
  mistakes: "Review mistakes",
  due: "Due for review",
};

const OPTION_COUNT = 4;

function distractors(item: LearningItem, pool: readonly LearningItem[], field: "term" | "answer", rng: Rng): string[] {
  const correct = item[field];
  const seen = new Set([correct.toLowerCase()]);
  const out: string[] = [];
  for (const other of shuffle(
    pool.filter((p) => p.kind === item.kind && p.id !== item.id),
    rng,
  )) {
    const value = other[field];
    if (seen.has(value.toLowerCase())) continue;
    seen.add(value.toLowerCase());
    out.push(value);
    if (out.length === OPTION_COUNT - 1) break;
  }
  return out;
}

export function choiceQuestion(
  item: LearningItem,
  type: ChoiceQuestion["type"],
  pool: readonly LearningItem[],
  rng: Rng,
  id: string,
): ChoiceQuestion {
  if (type === "letter-to-word" && item.kind !== "letter") throw new Error(`${item.term} is not a letter`);
  if (type !== "letter-to-word" && item.kind !== "code") throw new Error(`${item.term} is not a code`);
  const askMeaning = type !== "meaning-to-code";
  const field = askMeaning ? "answer" : "term";
  const answer = item[field];
  const options = shuffle([answer, ...distractors(item, pool, field, rng)], rng);
  const prompt =
    type === "code-to-meaning"
      ? "What does this code mean on the CHP card?"
      : type === "meaning-to-code"
        ? "Which code has this meaning on the CHP card?"
        : "Which word does the CHP card use for this letter?";
  return { id, type, itemIds: [item.id], prompt, subject: askMeaning ? item.term : item.answer, options, answer };
}

export function spellQuestion(letters: readonly LearningItem[], id: string): SpellQuestion {
  if (letters.length === 0 || letters.some((l) => l.kind !== "letter")) throw new Error("spell needs letters");
  return {
    id,
    type: "spell",
    itemIds: letters.map((l) => l.id),
    prompt: "Spell these letters using the CHP card words, in order.",
    subject: letters.map((l) => l.term).join(" "),
    answerWords: letters.map((l) => l.answer),
    answer: letters.map((l) => l.answer).join(" "),
  };
}

/** Lower-case letters only, so "X-ray", "xray" and "XRAY" compare equal. */
export function normalize(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** Splits free text into words, ignoring punctuation such as commas or dashes between words. */
export function words(s: string): string[] {
  return s
    .split(/[\s,;/|]+/)
    .map(normalize)
    .filter(Boolean);
}

export function isCorrect(q: Question, response: string): boolean {
  if (q.type === "spell") {
    const got = words(response);
    return got.length === q.answerWords.length && q.answerWords.every((w, i) => normalize(w) === got[i]);
  }
  return response === q.answer;
}

/**
 * Per-letter result for a spelling answer, so feedback can say which letter was
 * wrong instead of only "incorrect".
 */
export function spellBreakdown(q: SpellQuestion, response: string): { letter: string; expected: string; given: string | null; ok: boolean }[] {
  const got = words(response);
  const letters = q.subject.split(" ");
  return q.answerWords.map((expected, i) => ({
    letter: letters[i] ?? "?",
    expected,
    given: got[i] ?? null,
    ok: got[i] === normalize(expected),
  }));
}

/**
 * Orders items by how much they need practice: due items (longest overdue
 * first), then never-seen items, then the rest by lowest box.
 */
export function prioritize(items: readonly LearningItem[], progress: Record<string, ItemProgress>, now: number, rng: Rng): LearningItem[] {
  const rank = (i: LearningItem): [number, number] => {
    const p = progress[i.id];
    if (p === undefined) return [1, 0];
    if (isDue(p, now)) return [0, p.dueAt];
    return [2, p.box * 1e15 + p.dueAt];
  };
  return shuffle(items, rng).sort((a, b) => {
    const [ga, ka] = rank(a);
    const [gb, kb] = rank(b);
    return ga - gb || ka - kb;
  });
}

export function itemsForMode(mode: PracticeMode, items: readonly LearningItem[], progress: Record<string, ItemProgress>, now: number): LearningItem[] {
  switch (mode) {
    case "codes":
      return items.filter((i) => i.kind === "code");
    case "alphabet":
      return items.filter((i) => i.kind === "letter");
    case "mistakes":
      return items.filter((i) => needsReview(progress[i.id]));
    case "due":
      return items.filter((i) => isDue(progress[i.id], now));
    case "mixed":
      return [...items];
  }
}

function questionFor(item: LearningItem, all: readonly LearningItem[], rng: Rng, id: string, allowSpell: boolean): Question {
  if (item.kind === "code") return choiceQuestion(item, pick(["code-to-meaning", "meaning-to-code"] as const, rng), all, rng, id);
  if (allowSpell && rng() < 0.3) {
    const others = shuffle(
      all.filter((i) => i.kind === "letter" && i.id !== item.id),
      rng,
    ).slice(0, 2);
    return spellQuestion(shuffle([item, ...others], rng), id);
  }
  return choiceQuestion(item, "letter-to-word", all, rng, id);
}

export interface BuildOptions {
  mode: PracticeMode;
  items: readonly LearningItem[];
  progress: Record<string, ItemProgress>;
  now: number;
  rng: Rng;
  size?: number;
  /** Restrict the session to these item ids (used for "review this session's mistakes"). */
  onlyIds?: readonly string[];
}

export function buildQuestions({ mode, items, progress, now, rng, size = 10, onlyIds }: BuildOptions): Question[] {
  let candidates = itemsForMode(mode, items, progress, now);
  if (onlyIds) {
    const keep = new Set(onlyIds);
    candidates = candidates.filter((i) => keep.has(i.id));
  }
  const chosen = prioritize(candidates, progress, now, rng).slice(0, size);
  const allowSpell = mode !== "mistakes" && mode !== "due";
  return shuffle(chosen, rng).map((item, n) => questionFor(item, items, rng, `q${n + 1}`, allowSpell));
}

/** A short check at the end of a lesson: one choice question per item, up to `size`. */
export function lessonCheck(lessonItems: readonly LearningItem[], all: readonly LearningItem[], rng: Rng, size = 5): ChoiceQuestion[] {
  return shuffle(lessonItems, rng)
    .slice(0, size)
    .map((item, n) =>
      choiceQuestion(item, item.kind === "letter" ? "letter-to-word" : pick(["code-to-meaning", "meaning-to-code"] as const, rng), all, rng, `c${n + 1}`),
    );
}
