import { content } from "../content";
import { excerptParts } from "./SourceDetails";

it("finds every item's own entry inside its excerpt", () => {
  for (const item of content.items) {
    const [, match] = excerptParts(item);
    expect(match.toLowerCase()).toBe(`${item.term} ${item.answer}`.toLowerCase());
  }
});
