import { DAY_MS, intervalFor, isDue, needsReview, review, stateOf } from "./srs";

const T0 = Date.UTC(2026, 9, 1);

describe("review", () => {
  it("puts a first correct answer in box 2, due tomorrow", () => {
    const p = review(undefined, true, T0);
    expect(p).toMatchObject({ box: 2, seen: 1, correct: 1, lastResult: "correct", dueAt: T0 + DAY_MS });
  });

  it("puts a wrong answer in box 1, due immediately", () => {
    const p = review(review(undefined, true, T0), false, T0 + 2 * DAY_MS);
    expect(p).toMatchObject({ box: 1, seen: 2, correct: 1, lastResult: "wrong", dueAt: T0 + 2 * DAY_MS });
    expect(needsReview(p)).toBe(true);
  });

  it("does not promote an item answered before it is due", () => {
    const first = review(undefined, true, T0);
    const early = review(first, true, T0 + 1000);
    expect(early.box).toBe(2);
    expect(early.seen).toBe(2);
  });

  it("reaches mastery only across several days", () => {
    let p = review(undefined, true, T0);
    let now = T0;
    for (let i = 0; i < 10 && p.box < 5; i++) {
      now = p.dueAt;
      p = review(p, true, now);
    }
    expect(stateOf(p)).toBe("mastered");
    expect(now - T0).toBe((1 + 3 + 7) * DAY_MS);
  });

  it("clamps intervals and reports due items", () => {
    expect(intervalFor(0)).toBe(0);
    expect(intervalFor(9)).toBe(16 * DAY_MS);
    expect(isDue(undefined, T0)).toBe(false);
    expect(isDue(review(undefined, false, T0), T0)).toBe(true);
    expect(stateOf(undefined)).toBe("new");
  });
});
