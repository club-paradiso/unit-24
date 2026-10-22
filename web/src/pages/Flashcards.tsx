import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Link } from "react-router";
import { content, type LearningItem } from "../content";
import { Excerpt } from "../components/SourceDetails";
import { SpeechCoach } from "../components/SpeechCoach";
import { radioReading } from "../lib/radioSpeech";
import { LearnState, TrustBadges } from "../components/Status";
import { useT } from "../i18n";
import { haptic } from "../lib/haptics";
import { prioritize } from "../lib/quiz";
import { isDue } from "../lib/srs";
import { useProgress, useStore, useTitle } from "../state";
import { systemLabel } from "./labels";

type Deck = "all" | "codes" | "alphabet";
const DECKS: Deck[] = ["all", "codes", "alphabet"];
const DECK_SIZE = 15;
/** How far (px) a card must be dragged to count as a swipe. */
export const SWIPE_THRESHOLD = 90;

export function Flashcards() {
  const t = useT();
  useTitle(t("flash.title"));
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
  const [dx, setDx] = useState(0);
  const drag = useRef<{ x: number; id: number } | null>(null);
  const flipRef = useRef<HTMLButtonElement>(null);
  const knewRef = useRef<HTMLButtonElement>(null);

  const restart = (kind: Deck = deckKind) => {
    setDeckKind(kind);
    setRound((r) => r + 1);
    setIndex(0);
    setFlipped(false);
    setTally({ known: 0, again: 0 });
  };

  const item = deck[index];
  const finished = index >= deck.length;

  const flip = () => {
    if (!flipped) haptic("tap");
    setFlipped(true);
  };

  const grade = (known: boolean) => {
    if (!item || !flipped) return;
    store.recordResults({ [item.id]: known }, Date.now());
    haptic(known ? "success" : "tap");
    setTally((v) => (known ? { ...v, known: v.known + 1 } : { ...v, again: v.again + 1 }));
    setFlipped(false);
    setDx(0);
    setIndex((i) => i + 1);
    requestAnimationFrame(() => flipRef.current?.focus({ preventScroll: true }));
  };

  useEffect(() => {
    if (flipped) knewRef.current?.focus({ preventScroll: true });
  }, [flipped]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (flipped && e.key === "ArrowRight") grade(true);
      else if (flipped && e.key === "ArrowLeft") grade(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const onPointerDown = (e: ReactPointerEvent<HTMLElement>) => {
    if ((e.target as HTMLElement).closest("a, button")) return;
    drag.current = { x: e.clientX, id: e.pointerId };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: ReactPointerEvent<HTMLElement>) => {
    if (!drag.current || drag.current.id !== e.pointerId || !flipped) return;
    setDx(e.clientX - drag.current.x);
  };
  const onPointerUp = (e: ReactPointerEvent<HTMLElement>) => {
    if (!drag.current || drag.current.id !== e.pointerId) return;
    const moved = e.clientX - drag.current.x;
    drag.current = null;
    if (flipped && Math.abs(moved) >= SWIPE_THRESHOLD) grade(moved > 0);
    else if (Math.abs(moved) < 8) flip();
    setDx(0);
  };

  const now = Date.now();
  const due = content.items.filter((i) => isDue(progress.items[i.id], now)).length;
  const swipe = dx >= SWIPE_THRESHOLD ? "knew" : dx <= -SWIPE_THRESHOLD ? "again" : null;

  return (
    <div className="stack">
      <header className="stack-sm">
        <h1 className="h-compact">{t("flash.title")}</h1>
        <div className="segmented" role="group" aria-label={t("flash.deck")}>
          {DECKS.map((k) => (
            <button key={k} type="button" aria-pressed={deckKind === k} onClick={() => restart(k)}>
              {t(`deck.${k}`)}
            </button>
          ))}
        </div>
      </header>

      {finished ? (
        <section className="card card-success stack-sm" aria-labelledby="deck-done">
          <h2 id="deck-done">{t("flash.done")}</h2>
          <p>{t("flash.doneText", { known: tally.known, total: deck.length })}</p>
          {tally.again > 0 && <p>{t("flash.againText", { n: tally.again })}</p>}
          <p className="muted">{t("flash.dueNow", { n: due })}</p>
          <div className="actions">
            <button type="button" className="btn btn-primary" onClick={() => restart()}>
              {t("flash.another")}
            </button>
            <Link className="btn" to="/chp/practice">
              {t("flash.toPractice")}
            </Link>
          </div>
        </section>
      ) : (
        item && (
          <>
            <div className="session-bar" role="progressbar" aria-label={t("flash.progress")} aria-valuemin={0} aria-valuemax={deck.length} aria-valuenow={index}>
              <div style={{ width: `${(index / deck.length) * 100}%` }} />
            </div>
            <p className="muted small" aria-live="polite">
              {t("flash.counter", { n: index + 1, total: deck.length, known: tally.known, again: tally.again })}
            </p>
            <article
              className={`card flashcard ${flipped ? "is-flipped" : ""} ${swipe ? `swipe-${swipe}` : ""} ${dx ? "is-dragging" : ""}`}
              aria-label={t("flash.cardLabel", { n: index + 1 })}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={() => {
                drag.current = null;
                setDx(0);
              }}
              style={dx ? { transform: `translateX(${dx}px) rotate(${dx / 25}deg)` } : undefined}
            >
              {swipe && (
                <span className={`swipe-label swipe-label-${swipe}`} aria-hidden="true">
                  {swipe === "knew" ? t("flash.knew") : t("flash.again")}
                </span>
              )}
              <div className="flashcard-top">
                <span className="chip">{systemLabel(item.code_system, t)}</span>
                <LearnState progress={progress.items[item.id]} />
              </div>
              <p className="study-term" lang="en">
                {item.term}
              </p>
              <div aria-live="polite">
                {flipped ? (
                  <div className="stack-sm">
                    <p className="study-answer" lang="en">
                      {item.answer}
                    </p>
                    <TrustBadges item={item} compact />
                    <Excerpt item={item} />
                  </div>
                ) : (
                  <p className="muted">{item.kind === "letter" ? t("flash.askLetter") : t("flash.askCode")}</p>
                )}
              </div>
              <p className="flash-hint muted small" aria-hidden="true">
                {flipped ? t("flash.swipeHint") : t("flash.tapHint")}
              </p>
            </article>
            <SpeechCoach key={item.id} phrase={radioReading(item)} compact />
            <div className="sticky-actions">
              {flipped ? (
                <>
                  <button type="button" className="btn btn-bad btn-grow" onClick={() => grade(false)}>
                    ← {t("flash.again")}
                  </button>
                  <button ref={knewRef} type="button" className="btn btn-good btn-grow" onClick={() => grade(true)}>
                    {t("flash.knew")} →
                  </button>
                </>
              ) : (
                <button ref={flipRef} type="button" className="btn btn-primary btn-block" onClick={flip}>
                  {t("flash.show")}
                </button>
              )}
            </div>
          </>
        )
      )}
    </div>
  );
}
