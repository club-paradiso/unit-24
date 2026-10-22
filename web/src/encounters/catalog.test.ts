import { encounterCatalog, validateEncounterCatalog } from "./catalog";
import type { EncounterScenario } from "./types";

const clone = (): EncounterScenario[] => structuredClone(encounterCatalog) as EncounterScenario[];

describe("ENCOUNTER foundation catalog", () => {
  it("lists six distinct, bilingual, non-playable learning scenarios", () => {
    expect(encounterCatalog).toHaveLength(6);
    expect(new Set(encounterCatalog.map(s => s.id)).size).toBe(6);
    for (const s of encounterCatalog) {
      expect(s.stage).toBe("planned");
      expect(s.legalReview).toBe("pending");
      expect(s.sources).toEqual([]);
      expect(s.turns).toEqual([]);
      expect(s.jurisdiction).toEqual({ country: "US", state: null });
      expect(s.title.ko).toBeTruthy();
      expect(s.title.en).toBeTruthy();
      expect(s.learningGoals.length).toBeGreaterThan(0);
    }
  });

  it("rejects duplicated IDs and missing translated content", () => {
    const repeated = clone();
    repeated[1]!.id = repeated[0]!.id;
    expect(() => validateEncounterCatalog(repeated)).toThrow(/ID/);
    const untranslated = clone();
    untranslated[0]!.summary.en = "";
    expect(() => validateEncounterCatalog(untranslated)).toThrow(/localized/);
  });

  it("does not allow premature playable content without editorial evidence", () => {
    const items = clone();
    items[0]!.stage = "playable";
    expect(() => validateEncounterCatalog(items)).toThrow(/editorial review/);
    const planned = clone();
    planned[0]!.turns.push({ id: "x", speaker: "officer", utterance: "Hello", translation: { ko: "안녕하세요", en: "Hello" }, responses: [] });
    expect(() => validateEncounterCatalog(planned)).toThrow(/Planned scenarios/);
  });

  it("rejects a dangling dialogue branch target", () => {
    const items = clone();
    const scenario = items[0]!;
    scenario.stage = "playable";
    scenario.legalReview = "reviewed";
    scenario.sources = [{ title: "Editorial test fixture", url: "https://example.org/test", checkedAt: "2026-10-22", jurisdiction: "US" }];
    scenario.turns = [{
      id: "start", speaker: "officer", utterance: "Hello", translation: { ko: "안녕하세요", en: "Hello" },
      responses: [{ id: "response-1", utterance: "Hello", feedback: { ko: "예시", en: "Example" }, nextTurnId: "missing" }],
    }];
    expect(() => validateEncounterCatalog(items)).toThrow(/branch target/);
  });
});
