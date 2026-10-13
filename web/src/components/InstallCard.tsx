import { useEffect, useState } from "react";
import { useT } from "../i18n";
import { canPromptInstall, isIos, isStandalone, onInstallChange, promptInstall } from "../lib/install";
import { Icon } from "./Icon";

const DISMISS_KEY = "unit24.install-dismissed";

/** Offers "add to home screen" once, on phones where the app is not installed yet. */
export function InstallCard({ always = false }: { always?: boolean }) {
  const t = useT();
  const [, force] = useState(0);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return window.localStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });
  useEffect(() => onInstallChange(() => force((n) => n + 1)), []);

  if (isStandalone()) return always ? <p className="muted">{t("install.installed")}</p> : null;
  const prompt = canPromptInstall();
  const ios = isIos();
  if (!always && (dismissed || (!prompt && !ios))) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* fine: shows again next visit */
    }
  };

  return (
    <section className="card install-card stack-sm" aria-labelledby="install-h">
      <h2 id="install-h" className="h-small">
        <Icon name="download" /> {t("install.title")}
      </h2>
      <p className="small">{t("install.text")}</p>
      {prompt ? (
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => void promptInstall()}>
            {t("install.button")}
          </button>
          {!always && (
            <button type="button" className="btn btn-quiet" onClick={dismiss}>
              {t("common.later")}
            </button>
          )}
        </div>
      ) : ios ? (
        <>
          <p className="small">{t("install.ios")}</p>
          {!always && (
            <button type="button" className="btn btn-quiet btn-small" onClick={dismiss}>
              {t("common.later")}
            </button>
          )}
        </>
      ) : (
        <p className="small muted">{t("install.unsupported")}</p>
      )}
    </section>
  );
}
