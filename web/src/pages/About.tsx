import { Link } from "react-router";
import { content } from "../content";
import { useTitle } from "../state";

export function About() {
  useTitle("Sources & verification");
  const src = content.source;
  const c = content.counts;
  return (
    <div className="stack-lg prose">
      <header className="stack-sm">
        <h1>Sources & verification</h1>
        <p className="lead">What Unit-24 teaches, where it comes from, and how far it has been checked.</p>
      </header>

      <section aria-labelledby="src-h">
        <h2 id="src-h">The source</h2>
        <p>
          All current content comes from one document: <strong>{src.title}</strong>, published by the {src.issuing_agency}. The file name gives the version as{" "}
          <strong>{src.version}</strong>; the card's printed revision and effective date have not been confirmed.
        </p>
        <ul>
          <li>
            Original: <a href={src.url}>{src.url}</a>
          </li>
          <li>
            Fingerprint: <code className="hash">sha256:{src.sha256}</code> ({src.byte_length.toLocaleString()} bytes, {src.page_count} pages), retrieved{" "}
            {src.retrieved_at.slice(0, 10)}.
          </li>
          <li>{src.document_note}</li>
        </ul>
      </section>

      <section aria-labelledby="how-h">
        <h2 id="how-h">How entries were checked</h2>
        <p>
          Text was extracted from the card automatically, then an automated (AI agent) review compared each of the {c.reviewed} extracted entries with the
          rendered card. Unit-24 teaches only the entries that review found to match the card exactly:
        </p>
        <ul>
          <li>
            <strong>{c.teachable_codes} radio codes</strong> (10-codes and 11-codes) whose meaning matched word for word;
          </li>
          <li>
            <strong>the {c.teachable_letters}-letter spelling alphabet</strong> printed on page 2. It is the card's own alphabet — it uses “Yellow” for Y, so it
            is neither the APCO 1941 alphabet (“Young”) nor the NATO alphabet.
          </li>
        </ul>
        <p>
          The other <strong>{c.excluded} entries</strong> were read wrongly — usually because text from a neighbouring column ran into them or a
          continuation line was lost. They are listed in the <Link to="/chp/reference">reference</Link> without their (wrong) extracted meaning.
        </p>
      </section>

      <section aria-labelledby="status-h">
        <h2 id="status-h">What the labels mean</h2>
        <dl className="facts">
          <dt>Source-matched</dt>
          <dd>An automated review found the entry exactly as shown on the card. It does not mean the entry is correct for current operations.</dd>
          <dt>Not human-verified</dt>
          <dd>
            No human reviewer has accepted the entry yet. The research corpus requires that before anything is approved as a training answer, so every entry
            is still marked <code>RESEARCH_ONLY</code>. {c.human_verified} of {c.teachable} entries are human-verified.
          </dd>
          <dt>Current use unknown</dt>
          <dd>Nothing confirms that CHP still uses this card or that it has not been revised since.</dd>
        </dl>
      </section>

      <section aria-labelledby="lim-h">
        <h2 id="lim-h">Limitations</h2>
        <ul>
          <li>The card lists meanings only. Unit-24 does not add usage examples, because the source gives none and inventing them would not be sourced.</li>
          <li>Codes are agency-specific. The same code can mean something different at another agency; nothing here is borrowed from other agencies.</li>
          <li>This is a study aid. It is not an operational reference and must not be used to communicate in a real emergency.</li>
          <li>Progress is stored only in this browser.</li>
        </ul>
      </section>
    </div>
  );
}
