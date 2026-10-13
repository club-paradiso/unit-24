import fixture from "./fixture.jsonl?raw";
import { draftProblem, reviewEntries, today, toJsonl, toRecord, type Draft } from "./records";

const entries = reviewEntries();
const byTerm = (t: string, taught: boolean) => entries.find((e) => e.term === t && e.taught === taught)!;
const draft = (d: Partial<Draft>): Draft => ({ decision: "ACCEPT", meaning: "", notes: "", decidedOn: "2026-10-13", ...d });

describe("review records", () => {
  it("lists all 85 reviewed entries, withholding rejected meanings", () => {
    expect(entries).toHaveLength(85);
    expect(entries.filter((e) => e.taught)).toHaveLength(50);
    for (const e of entries.filter((x) => !x.taught)) expect(e.shownAnswer).toBeNull();
  });

  it("serialises exactly what the Python validator accepts (shared fixture)", () => {
    const out = toJsonl([
      toRecord(byTerm("10-1", true), draft({ decision: "ACCEPT" }), " Test Reviewer "),
      toRecord(byTerm("10-4", false), draft({ decision: "CORRECT", meaning: "  Message   received " }), "Test Reviewer"),
      toRecord(byTerm("10-10", false), draft({ decision: "REJECT", notes: "Extraction merged two columns" }), "Test Reviewer"),
    ]);
    expect(out).toBe(fixture);
  });

  it("mirrors the validator's rules", () => {
    expect(draftProblem(byTerm("10-4", false), draft({ decision: "ACCEPT" }))).toBe("acceptExcluded");
    expect(draftProblem(byTerm("10-1", true), draft({ decision: "REJECT" }))).toBe("rejectNoNotes");
    expect(draftProblem(byTerm("10-4", false), draft({ decision: "CORRECT" }))).toBe("correctNoMeaning");
    expect(draftProblem(byTerm("10-4", false), draft({ decision: "CORRECT", meaning: "Not on the card" }))).toBe("correctNotInExcerpt");
    expect(draftProblem(byTerm("10-4", false), draft({ decision: "CORRECT", meaning: "message RECEIVED" }))).toBeNull();
    expect(draftProblem(byTerm("10-1", true), draft({ decision: "ACCEPT" }))).toBeNull();
  });

  it("formats today as a local date", () => {
    expect(today(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
