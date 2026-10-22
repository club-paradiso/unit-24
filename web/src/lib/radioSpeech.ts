import type { LearningItem } from "../content/types";

/**
 * Learner-friendly convention, not a certified CHP on-air pronunciation standard.
 * This separates the spoken name from the radio code's operational meaning.
 */
const ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
  "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"];
const TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"];

export function numberReading(value: number): string {
  if (!Number.isInteger(value) || value < 0 || value > 99) return String(value);
  if (value < 20) return ONES[value]!;
  const ten = Math.floor(value / 10);
  const one = value % 10;
  return one === 0 ? TENS[ten]! : `${TENS[ten]} ${ONES[one]}`;
}

export function radioReading(item: Pick<LearningItem, "term" | "answer" | "kind">): string {
  if (item.kind === "letter") return item.answer.trim();
  const match = /^(10|11)-(\d{1,2})$/.exec(item.term.trim());
  if (!match) return item.term.trim();
  const prefix = match[1] === "10" ? "ten" : "eleven";
  return `${prefix} ${numberReading(Number(match[2]))}`;
}

/** A plain-language pronunciation cue, deliberately separate from asserted radio procedure. */
export function radioDisplayReading(item: Pick<LearningItem, "term" | "answer" | "kind">): string {
  if (item.kind === "letter") return `${item.term} as in ${item.answer}`;
  return radioReading(item);
}

export function normalizeSpeech(text: string): string {
  return text
    .toLowerCase()
    .replace(/\b(10|11)[-\s](\d{1,2})\b/g, (_match, prefix: string, suffix: string) =>
      `${prefix === "10" ? "ten" : "eleven"} ${numberReading(Number(suffix))}`)
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function heardSimilarity(heard: string, expected: string): "similar" | "partial" | "different" {
  const a = normalizeSpeech(heard), b = normalizeSpeech(expected);
  if (!a || !b) return "different";
  if (a === b) return "similar";
  const wordsA = a.split(" "), wordsB = b.split(" ");
  const intersection = wordsB.filter(w => wordsA.includes(w)).length;
  const ratio = intersection / Math.max(wordsB.length, wordsA.length);
  return ratio >= 0.7 ? "similar" : ratio >= 0.3 ? "partial" : "different";
}
