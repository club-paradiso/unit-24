import { Link } from "react-router";
import { content } from "../content";
import { useT } from "../i18n";
import { useTitle } from "../state";

export function About() {
  const t = useT();
  useTitle(t("about.title"));
  const src = content.source;
  const c = content.counts;
  return (
    <div className="stack-lg prose">
      <header className="stack-sm">
        <h1>{t("about.title")}</h1>
        <p className="lead">{t("about.lead")}</p>
      </header>

      <section aria-labelledby="src-h">
        <h2 id="src-h">{t("about.sourceH")}</h2>
        <p>{t("about.sourceText", { title: src.title, agency: src.issuing_agency, version: src.version })}</p>
        <ul>
          <li>
            {t("about.original")}{" "}
            <a href={src.url} lang="en">
              {src.url}
            </a>
          </li>
          <li>
            {t("about.fingerprint")} <code className="hash">sha256:{src.sha256}</code>
          </li>
          <li>{t("about.notCommitted")}</li>
        </ul>
      </section>

      <section aria-labelledby="how-h">
        <h2 id="how-h">{t("about.howH")}</h2>
        <p>{t("about.howText", { n: c.reviewed })}</p>
        <ul>
          <li>{t("about.howCodes", { n: c.teachable_codes })}</li>
          <li>{t("about.howAlphabet", { n: c.teachable_letters })}</li>
        </ul>
        <p>
          {t("about.howExcluded", { n: c.excluded })} <Link to="/chp/reference">{t("ref.title")}</Link>
        </p>
      </section>

      <section aria-labelledby="status-h">
        <h2 id="status-h">{t("about.labelsH")}</h2>
        <dl className="facts">
          <dt>{t("trust.sourceMatched")}</dt>
          <dd>{t("about.labelSourceMatched")}</dd>
          <dt>{t("trust.notVerified")}</dt>
          <dd>{t("about.labelNotVerified")}</dd>
          <dt>{t("trust.humanVerified")}</dt>
          <dd>{t("about.labelVerified", { n: c.human_verified, total: c.teachable })}</dd>
          <dt>{t("trust.humanReading")}</dt>
          <dd>{t("about.labelHumanReading")}</dd>
          <dt>{t("trust.currentUnknown")}</dt>
          <dd>{t("about.labelCurrentUnknown")}</dd>
        </dl>
      </section>

      <section aria-labelledby="rev-h">
        <h2 id="rev-h">{t("about.reviewersH")}</h2>
        <p>
          {t("about.reviewersText", { n: c.reviewed })} <Link to="/review">{t("about.reviewLink")}</Link>
        </p>
      </section>

      <section aria-labelledby="privacy-h">
        <h2 id="privacy-h">{t("about.privacyH")}</h2>
        <p>{t("about.privacyText")}</p>
      </section>

      <section aria-labelledby="lim-h">
        <h2 id="lim-h">{t("about.limitsH")}</h2>
        <ul>
          <li>{t("about.limit1")}</li>
          <li>{t("about.limit2")}</li>
          <li>{t("about.limit3")}</li>
        </ul>
      </section>
    </div>
  );
}
