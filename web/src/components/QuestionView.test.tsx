import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { content } from "../content";
import { choiceQuestion, spellQuestion, type Question } from "../lib/quiz";
import { seeded } from "../lib/random";
import { renderWith } from "../test/render";
import { QuestionView, type Answered } from "./QuestionView";

function Harness({ question, onAnswer }: { question: Question; onAnswer: (r: Record<string, boolean>) => void }) {
  const [answered, setAnswered] = useState<Answered | null>(null);
  return (
    <QuestionView
        question={question}
        answered={answered}
        nextLabel="Next question"
        onNext={() => {}}
        onAnswer={(response, correct, results) => {
          setAnswered({ response, correct });
          onAnswer(results);
        }}
    />
  );
}

const item = content.items.find((i) => i.term === "10-1")!;
const byTerm = (t: string) => content.items.find((i) => i.term === t)!;

it("answers with the number keys and shows the correct answer with its source", async () => {
  const q = choiceQuestion(item, "code-to-meaning", content.items, seeded(1), "q1");
  const onAnswer = vi.fn();
  renderWith(<Harness question={q} onAnswer={onAnswer} />);
  const wrongIndex = q.options.findIndex((o) => o !== q.answer);
  await userEvent.keyboard(String(wrongIndex + 1));
  expect(onAnswer).toHaveBeenCalledWith({ [item.id]: false });
  expect(screen.getByText("Not quite")).toBeInTheDocument();
  expect(screen.getByText("Correct answer")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "See source for 10-1" })).toHaveAttribute("href", `/chp/items/${item.id}`);
  expect(screen.getByRole("button", { name: "Next question" })).toHaveFocus();
  for (const b of screen.getAllByRole("button", { pressed: false })) expect(b).toBeDisabled();
});

it("grades spelling per letter", async () => {
  const q = spellQuestion([byTerm("C"), byTerm("H"), byTerm("P")], "s1");
  const onAnswer = vi.fn();
  renderWith(<Harness question={q} onAnswer={onAnswer} />);
  await userEvent.type(screen.getByLabelText(/your answer/i), "Charles Harry Paul{Enter}");
  expect(onAnswer).toHaveBeenCalledWith({ [byTerm("C").id]: true, [byTerm("H").id]: false, [byTerm("P").id]: true });
  expect(screen.getByText(/“harry”/)).toBeInTheDocument();
});

it("speaks Korean by default while keeping the English answer text", async () => {
  const q = choiceQuestion(item, "code-to-meaning", content.items, seeded(1), "q1");
  renderWith(<Harness question={q} onAnswer={() => {}} />, "ko");
  expect(screen.getByText("CHP 카드에서 이 코드의 뜻은?")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Reception poor/ }));
  expect(screen.getByText("정답입니다")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "10-1 출처 보기" })).toBeInTheDocument();
});
