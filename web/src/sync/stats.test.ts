import { commitBody, sendStats, sessionStats, setStatsEnabled } from "./stats";

describe("anonymous statistics", () => {
  it("totals right and wrong answers per entry", () => {
    expect(sessionStats("mixed", [{ a: true }, { a: false, b: true }, { b: true }])).toEqual({
      mode: "mixed",
      n: 3,
      results: { a: { c: 1, w: 1 }, b: { c: 2, w: 0 } },
    });
    expect(sessionStats("mixed", [])).toBeNull();
  });

  it("builds a create-only Firestore commit with a server timestamp and no identifiers", () => {
    const body = commitBody("p1", "doc1", "v1", { mode: "codes", n: 1, results: { a: { c: 1, w: 0 } } });
    const w = body.writes[0]!;
    expect(w.update.name).toBe("projects/p1/databases/(default)/documents/session_stats/doc1");
    expect(Object.keys(w.update.fields).sort()).toEqual(["contentVersion", "mode", "n", "results", "schema"]);
    expect(w.updateTransforms).toEqual([{ fieldPath: "at", setToServerValue: "REQUEST_TIME" }]);
    expect(w.currentDocument).toEqual({ exists: false });
  });

  it("sends nothing when turned off or not configured, and never throws", async () => {
    const stats = sessionStats("mixed", [{ a: true }]);
    const fetchImpl = vi.fn(async () => new Response("{}", { status: 200 }));
    expect(await sendStats(null, "v", stats, fetchImpl)).toBe(false);
    setStatsEnabled(false);
    expect(await sendStats({ projectId: "p", apiKey: "k" }, "v", stats, fetchImpl)).toBe(false);
    setStatsEnabled(true);
    expect(await sendStats({ projectId: "p", apiKey: "k" }, "v", stats, fetchImpl)).toBe(true);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const failing = vi.fn(async () => {
      throw new Error("offline");
    });
    expect(await sendStats({ projectId: "p", apiKey: "k" }, "v", stats, failing)).toBe(false);
  });
});
