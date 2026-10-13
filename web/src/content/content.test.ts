import raw from "./chp.json";
import { content, getItem, lessonItems, validateBundle } from ".";

describe("content bundle", () => {
  it("has the audited counts and only unverified, traceable items", () => {
    expect(content.counts).toMatchObject({ teachable: 50, teachable_codes: 24, teachable_letters: 26, human_verified: 0 });
    for (const item of content.items) {
      expect(item.status.human_verified).toBe(false);
      expect(item.status.currentness).toBe("UNKNOWN");
      expect(item.excerpt.toLowerCase()).toContain(item.answer.toLowerCase());
    }
  });

  it("resolves every lesson item", () => {
    for (const lesson of content.lessons) expect(lessonItems(lesson)).toHaveLength(lesson.item_ids.length);
    expect(getItem("missing")).toBeUndefined();
  });

  it("rejects a bundle that is not traceable", () => {
    const bad = structuredClone(raw) as { items: { excerpt: string }[] };
    bad.items[0]!.excerpt = "";
    expect(() => validateBundle(bad)).toThrow(/not traceable/);
    expect(() => validateBundle({ ...raw, schema_version: 1 })).toThrow(/schema_version/);
  });
});
