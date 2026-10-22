import { Link, useParams } from "react-router";
import { content, getItem } from "../content";
import { Excerpt, SourceDetails } from "../components/SourceDetails";
import { SpeechCoach } from "../components/SpeechCoach";
import { radioReading, radioDisplayReading } from "../lib/radioSpeech";
import { LearnState, TrustBadges, useLimitations } from "../components/Status";
import { useI18n } from "../i18n";
import { percent, relativeDue, shortDate } from "../lib/format";
import { useProgress, useTitle } from "../state";
import { lessonTitle } from "./Home";
import { NotFound } from "./NotFound";
import { systemLabel } from "./labels";

export function ItemDetail() {
  const { itemId = "" } = useParams();
  const item = getItem(itemId);
  if (!item) return <NotFound what="entry" />;
  return <Detail key={item.id} itemId={item.id} />;
}

function Detail({ itemId }: { itemId: string }) {
  const { t, lang } = useI18n();
  const item = getItem(itemId)!;
  const progress = useProgress();
  const limitations = useLimitations(item);
  useTitle(`${item.term} — ${item.answer}`);
  const p = progress.items[item.id];
  const idx = content.items.indexOf(item);
  const prev = content.items[idx - 1];
  const next = content.items[idx + 1];
  const lesson = content.lessons.find((l) => l.item_ids.includes(item.id));

  return (
    <div className="stack-lg">
      <header className="stack-sm">
        <p className="eyebrow">
          <Link to="/chp/reference">{t("ref.title")}</Link> · {systemLabel(item.code_system, t)}
        </p>
        <h1 className="item-heading" lang="en">
          <span className="study-term">{item.term}</span>
          <span className="study-answer">{item.answer}</span>
        </h1>
        <TrustBadges item={item} />
      </header>

      <section aria-label={lang === "ko" ? "발음과 말하기 연습" : "Pronunciation and speaking"} className="stack-sm">
        <p className="eyebrow">{lang === "ko" ? "이 코드는 이렇게 읽는 연습을 해요" : "Try reading the code aloud"}</p>
        <p lang="en" className="radio-reading">{radioDisplayReading(item)}</p>
        <SpeechCoach key={item.id} phrase={radioReading(item)} compact />
        <p className="muted small">{lang === "ko" ? "일반적인 학습용 읽기입니다. 실제 무전 발성과 다를 수 있어요." : "A learner-friendly reading, not a verified official broadcast."}</p>
      </section>
      <section className="stack" aria-labelledby="mine-h">
        <h2 id="mine-h">{t("detail.yourProgress")}</h2>
        {p ? (
          <p>
            <LearnState progress={p} /> {t("detail.stats", { seen: p.seen, pct: percent(p.correct, p.seen), last: shortDate(p.lastSeenAt, lang), due: relativeDue(p.dueAt, Date.now(), t) })}
          </p>
        ) : (
          <p>
            {t("detail.notStudied")}
            {lesson && (
              <>
                {" "}
                {t("detail.inLesson")} <Link to={`/chp/lessons/${lesson.id}`}>{lessonTitle(lesson, lang)}</Link>
              </>
            )}
          </p>
        )}
      </section>

      <section className="stack" aria-labelledby="src-h">
        <h2 id="src-h">{t("detail.sourceTitle")}</h2>
        <Excerpt item={item} />
        <SourceDetails item={item} />
      </section>

      <section className="stack" aria-labelledby="lim-h">
        <h2 id="lim-h">{t("detail.limitations")}</h2>
        <ul>
          {limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        {item.notes.length > 0 && (
          <details>
            <summary>{t("detail.notes")}</summary>
            <ul lang="en">
              {item.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <nav className="pager" aria-label={t("detail.neighbours")}>
        {prev ? (
          <Link to={`/chp/items/${prev.id}`} rel="prev">
            ← {prev.term}
          </Link>
        ) : (
          <span />
        )}
        {next && (
          <Link to={`/chp/items/${next.id}`} rel="next">
            {next.term} →
          </Link>
        )}
      </nav>
    </div>
  );
}
