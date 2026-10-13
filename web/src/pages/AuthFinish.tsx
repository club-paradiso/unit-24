import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useT } from "../i18n";
import { useTitle } from "../state";
import { useSync } from "../sync/context";

type Phase = "checking" | "needEmail" | "done" | "invalid" | "error" | "unconfigured";

/** Landing page for the sign-in link sent by email. */
export function AuthFinish() {
  const t = useT();
  useTitle(t("authFinish.title"));
  const { configured } = useSync();
  const [phase, setPhase] = useState<Phase>(configured ? "checking" : "unconfigured");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  const finish = async (address: string) => {
    try {
      const m = await import("../sync/firebase");
      await m.finishEmailLink(address, window.location.href);
      window.history.replaceState(null, "", "/auth/finish");
      setPhase("done");
    } catch (e) {
      setError((e as { code?: string }).code ?? String(e));
      setPhase("error");
    }
  };

  useEffect(() => {
    if (!configured) return;
    void (async () => {
      const m = await import("../sync/firebase");
      if (!(await m.isEmailLink(window.location.href))) return setPhase("invalid");
      const saved = window.localStorage.getItem(m.EMAIL_KEY);
      if (saved) await finish(saved);
      else setPhase("needEmail");
    })();
  }, [configured]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (email.trim()) void finish(email.trim());
  };

  return (
    <div className="stack">
      <h1>{t("authFinish.title")}</h1>
      {phase === "checking" && <p role="status">{t("authFinish.checking")}</p>}
      {phase === "needEmail" && (
        <form onSubmit={onSubmit} className="stack-sm">
          <label htmlFor="finish-email" className="label">
            {t("authFinish.confirmEmail")}
          </label>
          <input id="finish-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button type="submit" className="btn btn-primary">
            {t("authFinish.continue")}
          </button>
        </form>
      )}
      {phase === "done" && (
        <>
          <p role="status">{t("authFinish.done")}</p>
          <Link className="btn btn-primary" to="/">
            {t("authFinish.toHome")}
          </Link>
        </>
      )}
      {(phase === "invalid" || phase === "unconfigured") && <p>{t("authFinish.invalid")}</p>}
      {phase === "error" && <p role="alert">{t("authFinish.error", { reason: error })}</p>}
      {phase !== "done" && (
        <p>
          <Link to="/settings">{t("nav.settings")}</Link>
        </p>
      )}
    </div>
  );
}
