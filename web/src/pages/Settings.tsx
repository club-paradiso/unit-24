import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router";
import { assertImportContent } from "../lib/content-progress";
import { parseState } from "../lib/progress";
import { content } from "../content";
import { InstallCard } from "../components/InstallCard";
import { useI18n, type Lang } from "../i18n";
import { useStore, useTitle } from "../state";
import { AccountSection } from "../sync/AccountSection";

const HAPTICS_KEY = "unit24.haptics";

function readHaptics(): boolean {
  try {
    return window.localStorage.getItem(HAPTICS_KEY) !== "off";
  } catch {
    return true;
  }
}

export function Settings() {
  const { t, lang, setLang } = useI18n();
  useTitle(t("settings.title"));
  const store = useStore();
  const [message, setMessage] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [haptics, setHaptics] = useState(readHaptics);
  const fileRef = useRef<HTMLInputElement>(null);

  const toggleHaptics = (on: boolean) => {
    setHaptics(on);
    try {
      window.localStorage.setItem(HAPTICS_KEY, on ? "on" : "off");
    } catch {
      /* preference not saved */
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([store.exportJson()], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `unit24-progress-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage(t("settings.downloaded"));
  };

  const downloadRecovery = () => {
    const text = store.recoveryJson();
    if (text === null) return;
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = `unit24-recovery-${new Date().toISOString().slice(0, 10)}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const upload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const text = await file.text();
      assertImportContent(parseState(text));
      store.importJson(text);
      setMessage(t("settings.restored"));
    } catch (err) {
      setMessage(t("settings.restoreFailed", { reason: err instanceof Error ? err.message : String(err) }));
    }
  };

  return (
    <div className="stack-lg">
      <h1>{t("settings.title")}</h1>

      <section className="stack-sm" aria-labelledby="lang-h">
        <h2 id="lang-h">{t("settings.language")}</h2>
        <div className="segmented" role="group" aria-labelledby="lang-h">
          {(["ko", "en"] as Lang[]).map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)} lang={l}>
              {l === "ko" ? "한국어" : "English"}
            </button>
          ))}
        </div>
        <p className="muted small">{t("settings.languageNote")}</p>
      </section>

      <AccountSection />

      <section className="stack-sm" aria-labelledby="study-h">
        <h2 id="study-h">{t("settings.study")}</h2>
        <label className="switch">
          <input type="checkbox" checked={haptics} onChange={(e) => toggleHaptics(e.target.checked)} />
          <span>{t("settings.haptics")}</span>
        </label>
        <p className="muted small">{t("settings.hapticsNote")}</p>
      </section>

      <InstallCard always />

      <section className="stack-sm" aria-labelledby="data-h">
        <h2 id="data-h">{t("settings.data")}</h2>
        <p className="muted small">{t("settings.dataNote")}</p>
        {store.recoveryJson() !== null && <div className="card stack-sm">
          <p className="small">{t("settings.recoveryNote")}</p>
          <button type="button" className="btn" onClick={downloadRecovery}>{t("settings.recoveryDownload")}</button>
        </div>}
        <div className="actions">
          <button type="button" className="btn" onClick={download}>
            {t("settings.download")}
          </button>
          <button type="button" className="btn" onClick={() => fileRef.current?.click()}>
            {t("settings.restore")}
          </button>
          <input ref={fileRef} type="file" accept="application/json,.json" onChange={upload} hidden aria-hidden="true" tabIndex={-1} />
          {confirmReset ? (
            <>
              <button
                type="button"
                className="btn btn-bad"
                onClick={() => {
                  store.reset();
                  setConfirmReset(false);
                  setMessage(t("settings.erased"));
                }}
              >
                {t("settings.confirmReset")}
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => setConfirmReset(false)}>
                {t("common.cancel")}
              </button>
            </>
          ) : (
            <button type="button" className="btn btn-quiet" onClick={() => setConfirmReset(true)}>
              {t("settings.reset")}
            </button>
          )}
        </div>
        <p role="status" className="muted">
          {message}
        </p>
      </section>

      <section className="stack-sm" aria-labelledby="info-h">
        <h2 id="info-h">{t("settings.info")}</h2>
        <ul className="plain-list">
          <li>
            <Link to="/about">{t("settings.sources")}</Link>
          </li>
          <li>
            <Link to="/review">{t("settings.review")}</Link>
          </li>
          <li className="muted small">{t("settings.contentVersion", { v: content.content_version })}</li>
        </ul>
      </section>
    </div>
  );
}
