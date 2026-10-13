import { bump, dayKey, streak } from "./streak";

const at = (y: number, m: number, d: number, h = 12) => new Date(y, m - 1, d, h).getTime();

describe("streak", () => {
  it("counts consecutive days ending today or yesterday", () => {
    const activity = { "2026-10-10": 3, "2026-10-11": 1, "2026-10-12": 5 };
    expect(streak(activity, at(2026, 10, 12))).toBe(3);
    expect(streak(activity, at(2026, 10, 13))).toBe(3);
    expect(streak(activity, at(2026, 10, 14))).toBe(0);
    expect(streak({}, at(2026, 10, 14))).toBe(0);
  });

  it("crosses month boundaries", () => {
    expect(streak({ "2026-09-30": 1, "2026-10-01": 1 }, at(2026, 10, 1))).toBe(2);
  });

  it("bumps today's count and keeps a bounded history", () => {
    let a = bump({}, at(2026, 10, 12));
    a = bump(a, at(2026, 10, 12, 23));
    expect(a).toEqual({ "2026-10-12": 2 });
    for (let d = 1; d <= 10; d++) a = bump(a, at(2026, 11, d), 1, 5);
    expect(Object.keys(a)).toHaveLength(5);
    expect(dayKey(at(2026, 1, 5))).toBe("2026-01-05");
  });
});
