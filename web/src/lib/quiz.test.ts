import { content } from "../content";
import type { ChoiceQuestion, SpellQuestion } from "./quiz";
import { buildQuestions, choiceQuestion, isCorrect, lessonCheck, normalize, spellBreakdown, spellQuestion } from "./quiz";
import { seeded } from "./random";
import { review } from "./srs";

const items = content.items;
const codes = items.filter((i) => i.kind === "code");
const letters = items.filter((i) => i.kind === "letter");
const byTerm = (t: string) => items.find((i) => i.term === t)!;
const NOW = Date.UTC(2026, 9, 1);

describe("choice questions", () => {
  it("offers four distinct options drawn only from teachable answers", () => {
    const rng = seeded(1);
    for (const item of codes) {
      const q = choiceQuestion(item, "code-to-meaning", items, rng, "q");
      expect(q.options).toHaveLength(4);
      expect(new Set(q.options).size).toBe(4);
      expect(q.options).toContain(item.answer);
      for (const o of q.options) expect(codes.map((c) => c.answer)).toContain(o);
    }
  });

  it("asks meaning-to-code with codes as options", () => {
    const q = choiceQuestion(byTerm("10-1"), "meaning-to-code", items, seeded(2), "q");
    expect(q.subject).toBe("Reception poor");
    expect(q.answer).toBe("10-1");
    expect(isCorrect(q, "10-1")).toBe(true);
    expect(isCorrect(q, q.options.find((o) => o !== "10-1")!)).toBe(false);
  });

  it("asks letter-to-word with card words, including Yellow for Y", () => {
    const q = choiceQuestion(byTerm("Y"), "letter-to-word", items, seeded(3), "q");
    expect(q.answer).toBe("Yellow");
    expect(q.options.every((o) => letters.some((l) => l.answer === o))).toBe(true);
  });

  it("refuses to mix kinds", () => {
    expect(() => choiceQuestion(byTerm("A"), "code-to-meaning", items, seeded(1), "q")).toThrow();
    expect(() => choiceQuestion(byTerm("10-1"), "letter-to-word", items, seeded(1), "q")).toThrow();
  });
});

describe("spelling", () => {
  const q: SpellQuestion = spellQuestion([byTerm("C"), byTerm("H"), byTerm("P")], "s");

  it("accepts any case and separators", () => {
    expect(q.subject).toBe("C H P");
    expect(isCorrect(q, "Charles Henry Paul")).toBe(true);
    expect(isCorrect(q, "charles, henry,  PAUL")).toBe(true);
    expect(isCorrect(q, "Charles Henry")).toBe(false);
    expect(isCorrect(q, "Charlie Hotel Papa")).toBe(false);
  });

  it("explains which letter was wrong", () => {
    const b = spellBreakdown(q, "Charles Harry Paul");
    expect(b.map((x) => x.ok)).toEqual([true, false, true]);
    expect(b[1]).toMatchObject({ letter: "H", expected: "Henry", given: "harry" });
  });

  it("normalizes X-ray spellings", () => {
    expect(normalize("X-ray")).toBe(normalize("Xray"));
  });
});

describe("session building", () => {
  it("builds the requested number of questions without repeating an item", () => {
    const qs = buildQuestions({ mode: "mixed", items, progress: {}, now: NOW, rng: seeded(4), size: 10 });
    expect(qs).toHaveLength(10);
    const primary = qs.map((q) => q.itemIds[0]);
    expect(new Set(primary).size).toBe(10);
  });

  it("restricts by mode", () => {
    const qs = buildQuestions({ mode: "codes", items, progress: {}, now: NOW, rng: seeded(5), size: 30 });
    expect(qs).toHaveLength(24);
    expect(qs.every((q) => q.type === "code-to-meaning" || q.type === "meaning-to-code")).toBe(true);
    const alpha = buildQuestions({ mode: "alphabet", items, progress: {}, now: NOW, rng: seeded(5) });
    expect(alpha.every((q) => q.type === "letter-to-word" || q.type === "spell")).toBe(true);
  });

  it("puts due items first and only reviews mistakes in mistakes mode", () => {
    const wrong = byTerm("10-9");
    const progress = { [wrong.id]: review(undefined, false, NOW - 1000) };
    const mistakes = buildQuestions({ mode: "mistakes", items, progress, now: NOW, rng: seeded(6) });
    expect(mistakes.map((q) => q.itemIds[0])).toEqual([wrong.id]);
    const mixed = buildQuestions({ mode: "mixed", items, progress, now: NOW, rng: seeded(6), size: 3 });
    expect(mixed.flatMap((q) => q.itemIds)).toContain(wrong.id);
    expect(buildQuestions({ mode: "due", items, progress: {}, now: NOW, rng: seeded(6) })).toEqual([]);
  });

  it("can be limited to specific ids", () => {
    const only = [byTerm("10-1").id, byTerm("11-98").id];
    const qs = buildQuestions({ mode: "mixed", items, progress: {}, now: NOW, rng: seeded(7), onlyIds: only });
    expect(qs.map((q) => q.itemIds[0]).sort()).toEqual([...only].sort());
  });

  it("is deterministic for a seed", () => {
    const a = buildQuestions({ mode: "mixed", items, progress: {}, now: NOW, rng: seeded(8) });
    const b = buildQuestions({ mode: "mixed", items, progress: {}, now: NOW, rng: seeded(8) });
    expect(a).toEqual(b);
  });
});

describe("lesson check", () => {
  it("asks about lesson items only", () => {
    const lesson = content.lessons[0]!;
    const lessonItems = lesson.item_ids.map((id) => items.find((i) => i.id === id)!);
    const qs: ChoiceQuestion[] = lessonCheck(lessonItems, items, seeded(9));
    expect(qs).toHaveLength(5);
    for (const q of qs) expect(lesson.item_ids).toContain(q.itemIds[0]);
  });
});
