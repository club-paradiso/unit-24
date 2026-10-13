import { render, screen } from "@testing-library/react";
import { content } from "../content";
import type { LearningItem } from "../content/types";
import { TrustBadges } from "./Status";

const base = content.items[0]!;
const variant = (status: Partial<LearningItem["status"]>, human: LearningItem["review"]["human"] = []): LearningItem => ({
  ...base,
  status: { ...base.status, ...status },
  review: { ...base.review, human },
});

it("says not human-verified when no person has reviewed the entry", () => {
  render(<TrustBadges item={base} />);
  expect(screen.getByText("Not human-verified")).toBeInTheDocument();
  expect(screen.queryByText("Human-verified")).toBeNull();
});

it("shows a human-verified badge naming the reviewer", () => {
  render(<TrustBadges item={variant({ human_verified: true, human_review: "accepted" }, [{ reviewer: "R. Person", reviewed_at: "2026-10-13", decision: "ACCEPT", notes: "" }])} />);
  expect(screen.getByText("Human-verified")).toHaveAttribute("title", "Verified by R. Person on 2026-10-13");
  expect(screen.queryByText("Not human-verified")).toBeNull();
});

it("distinguishes a human reading from an automated match, and disputes", () => {
  render(<TrustBadges item={variant({ human_verified: true, human_review: "corrected", answer_basis: "human_reading" })} />);
  expect(screen.getByText("Read from the card by a person")).toBeInTheDocument();
  render(<TrustBadges item={variant({ human_review: "disputed" })} />);
  expect(screen.getByText("Reviewers disagree")).toBeInTheDocument();
});
