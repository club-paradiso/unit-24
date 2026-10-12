import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { content, SYSTEM_LABEL, type LearningItem } from "../content";
import { Excerpt } from "../components/SourceDetails";
import { LearnState, TrustBadges } from "../components/Status";
import { prioritize } from "../lib/quiz";
import { isDue } from "../lib/srs";
import { useProgress, useStore, useTitle } from "../state";

type Deck = "all" | "codes" | "alphabet";
const DECK_LABEL: Record<Deck, string> = { all: "Everything", codes: "Codes", alphabet: "Card alphabet" };
const DECK_SIZE = 15;

export function Flashcards() {
  useTitle("Flashcards");
  const store = useStore();
  const progress = useProgress();
  const [deckKind, setDeckKind] = useState<Deck>("all");
  const [round, setRound] = useState(0);
  const deck = useMemo<LearningItem[]>(() => {
    const pool = content.items.filter((i) => deckKind === "all" || (deckKind === "codes" ? i.kind === "code" : i.kind === "letter"));
    return prioritize(pool, store.getState().items, Date.now(), Math.random).slice(0, DECK_SIZE);
  }, [deckKind, round, store]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [tally, setTally] = useState({ known: 0, again: 0 });
  const flipRef = useRef<HTMLButtonElement>(null);
  const gradeRef = useRef<HTMLButtonElement>(null);

  const restart = (kind: Deck = deckKind) => {
    setDeckKind(kind);
    setRound((r) => r + 1);
    setIndex(0);
    setFlipped(false);
    setTally({ known: 0, again: 0 });
  };

  const item = deck[index];
  const finished = index >= deck.length;

  useEffect(() => {
    if (flipped) gradeRef.current?.focus();
  }, [flipped]);

  const grade = (known: boolean) => {
    if (!item) return;
    store.recordResults({ [item.id]: known }, Date.now());
    setTally((t) => (known ? { ...t, known: t.known + 1 } : { ...t, again: t.again + 1 }));
    setFlipped(false);
    setIndex((i) => i + 1);
    requestAnimationFrame(() => flipRef.current?.focus());
  };

  const now = Date.now();
  const due = content.items.filter((i) => isDue(progress.items[i.id], now)).length;

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp">CHP</Link>
        </p>
        <h1>Flashcards</h1>
        <p className="lead">Recall the answer, then flip the card and say honestly whether you knew it. Due and weak items come first.</p>
      </header>

      <div className="segmented" role="group" aria-label="Deck">
        {(Object.keys(DECK_LABEL) as Deck[]).map((k) => (
          <button key={k} type="button" aria-pressed={deckKind === k} onClick={() => restart(k)}>
            {DECK_LABEL[k]}
          </button>
        ))}
      </div>

      {finished ? (
        <section className="card card-success" aria-labelledby="deck-done">
          <h2 id="deck-done">Deck finished</h2>
          <p>
            You knew {tally.known} of {deck.length}. {tally.again > 0 ? `${tally.again} will come back sooner for review.` : ""}
          </p>
          <p className="muted">{due} items are due for review now.</p>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => restart()}>
              Another deck
            </button>
            <Link className="btn" to="/chp/practice">
              Practice with questions
            </Link>
          </div>
        </section>
      ) : (
        item && (
          <>
            <p className="muted" aria-live="polite">
              Card {index + 1} of {deck.length} · knew {tally.known} · again {tally.again}
            </p>
            <article className={`card flashcard ${flipped ? "is-flipped" : ""}`} aria-label={`Flashcard ${index + 1}`}>
              <div className="flashcard-top">
                <span className="chip">{SYSTEM_LABEL[item.code_system]}</span>
                <LearnState progress={progress.items[item.id]} />
              </div>
              <p className="study-term">{item.term}</p>
              <div aria-live="polite">
                {flipped ? (
                  <div className="stack-sm">
                    <p className="study-answer">{item.answer}</p>
                    <TrustBadges item={item} compact />
                    <Excerpt item={item} />
                  </div>
                ) : (
                  <p className="muted">{item.kind === "letter" ? "Which word does the card use for this letter?" : "What does this code mean?"}</p>
                )}
              </div>
            </article>
            {flipped ? (
              <div className="actions grade">
                <button type="button" className="btn btn-bad" onClick={() => grade(false)}>
                  Again
                </button>
                <button ref={gradeRef} type="button" className="btn btn-good" onClick={() => grade(true)}>
                  I knew it
                </button>
              </div>
            ) : (
              <div className="actions">
                <button ref={flipRef} type="button" className="btn btn-primary" onClick={() => setFlipped(true)}>
                  Show answer
                </button>
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
