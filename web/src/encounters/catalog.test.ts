import { encounterCatalog, validateEncounterCatalog } from "./catalog";
import type { EncounterScenario } from "./types";

const clone = (): EncounterScenario[] => structuredClone(encounterCatalog) as EncounterScenario[];

describe("ENCOUNTER foundation catalog", () => {
  it("lists five planned topics and one clearly labeled language-only pilot", () => {
    expect(encounterCatalog).toHaveLength(6);
    expect(new Set(encounterCatalog.map(s => s.id)).size).toBe(6);
    expect(encounterCatalog.filter(s => s.stage === "planned")).toHaveLength(5);
    expect(encounterCatalog.filter(s => s.stage === "pilot")).toHaveLength(1);
    for (const s of encounterCatalog) {
      expect(s.legalReview).toBe("pending");
      if (s.stage === "planned") {
        expect(s.sources).toEqual([]);
        expect(s.turns).toEqual([]);
      } else {
        expect(s.sources.length).toBeGreaterThan(0);
        expect(s.turns.length).toBeGreaterThan(1);
      }
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
    expect(() => validateEncounterCatalog(items)).toThrow(/appropriate review state/);
    const planned = clone();
    planned[1]!.turns.push({ id: "x", speaker: "officer", utterance: "Hello", translation: { ko: "안녕하세요", en: "Hello" }, responses: [] });
    expect(() => validateEncounterCatalog(planned)).toThrow(/Planned scenarios/);
  });

  it("rejects a dangling dialogue branch target", () => {
    const items = clone();
    const scenario = items[0]!;
    scenario.turns = [{
      id: "start", speaker: "officer", utterance: "Hello", translation: { ko: "안녕하세요", en: "Hello" },
      responses: [{ id: "response-1", utterance: "Hello", feedback: { ko: "예시", en: "Example" }, languageRating: "natural", nextTurnId: "missing" }],
    }];
    expect(() => validateEncounterCatalog(items)).toThrow(/branch target/);
  });
});

describe("Traffic Stop pilot routes", () => {
  it("offers safe language-practice branches that all reach a conclusion", () => {
    const s = encounterCatalog.find(s => s.id === "traffic-stop")!;
    expect(s.stage).toBe("pilot");
    expect(s.legalReview).toBe("pending");
    expect(s.jurisdiction.state).toBeNull();
    const seen = new Set<string>();
    const walk = (id: string, depth = 0): void => {
      expect(depth).toBeLessThan(12);
      if (seen.has(id)) return;
      seen.add(id);
      const turn = s.turns.find(t => t.id === id)!;
      expect(turn).toBeDefined();
      for (const option of turn.responses) {
        expect(option.languageRating).toMatch(/natural|acceptable|needs_clarification/);
        if (option.nextTurnId !== null) walk(option.nextTurnId, depth + 1);
      }
    };
    walk(s.turns[0]!.id);
    expect(seen.size).toBe(s.turns.length);
  });
});
