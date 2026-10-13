import { useState, type FormEvent } from "react";
import { useI18n } from "../i18n";
import { dateTime } from "../lib/format";
import { useSync } from "./context";
import { setStatsEnabled, statsEnabled } from "./stats";

/** Sign-in, sync status and privacy choices. */
export function AccountSection() {
  const { t, lang } = useI18n();
  const { configured, account, snapshot, connect, syncNow } = useSync();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [stats, setStats] = useState(statsEnabled);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const run = async (fn: () => Promise<void>, done?: string) => {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      if (done) setMessage(done);
    } catch (e) {
      const code = (e as { code?: string }).code;
      setMessage(code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request" ? t("account.cancelled") : t("account.failed", { reason: code ?? String(e) }));
    } finally {
      setBusy(false);
    }
  };

  const onEmail = (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    void run(async () => (await connect()).sendEmailLink(email.trim(), lang), t("account.linkSent", { email: email.trim() }));
  };

  const statsToggle = (
    <label className="switch">
      <input
        type="checkbox"
        checked={stats}
        onChange={(e) => {
          setStats(e.target.checked);
          setStatsEnabled(e.target.checked);
        }}
      />
      <span>{t("account.stats")}</span>
    </label>
  );

  if (!configured) {
    return (
      <section className="stack-sm" aria-labelledby="account-h">
        <h2 id="account-h">{t("account.title")}</h2>
        <p className="muted small">{t("account.unavailable")}</p>
      </section>
    );
  }

  return (
    <section className="stack-sm" aria-labelledby="account-h">
      <h2 id="account-h">{t("account.title")}</h2>
      {account ? (
        <div className="card stack-sm">
          <p>{t("account.signedInAs", { who: account.email ?? t("account.googleUser") })}</p>
          <p className="muted small" role="status">
            {snapshot.status === "syncing"
              ? t("account.syncing")
              : snapshot.status === "synced" && snapshot.lastSyncedAt
                ? t("account.synced", { at: dateTime(snapshot.lastSyncedAt, lang) })
                : snapshot.status === "offline"
                  ? t("account.offline")
                  : snapshot.status === "error"
                    ? t("account.syncError", { reason: snapshot.error ?? "" })
                    : t("account.syncIdle")}
          </p>
          <div className="actions">
            <button type="button" className="btn" disabled={busy || snapshot.status === "syncing"} onClick={() => void run(syncNow)}>
              {t("account.syncNow")}
            </button>
            <button type="button" className="btn btn-quiet" disabled={busy} onClick={() => void run(async () => (await connect()).signOutAccount(), t("account.signedOut"))}>
              {t("account.signOut")}
            </button>
          </div>
          {confirmDelete ? (
            <div className="actions">
              <button
                type="button"
                className="btn btn-bad"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    const api = await connect();
                    await api.deleteCloudProgress(account.uid);
                    await api.signOutAccount();
                    setConfirmDelete(false);
                  }, t("account.deleted"))
                }
              >
                {t("account.confirmDelete")}
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => setConfirmDelete(false)}>
                {t("common.cancel")}
              </button>
            </div>
          ) : (
            <button type="button" className="btn btn-quiet btn-small" onClick={() => setConfirmDelete(true)}>
              {t("account.delete")}
            </button>
          )}
        </div>
      ) : (
        <div className="card stack-sm">
          <p className="small">{t("account.why")}</p>
          <button type="button" className="btn btn-block" disabled={busy} onClick={() => void run(async () => (await connect()).signInWithGoogle(lang))}>
            {t("account.google")}
          </button>
          <p className="muted small or-line">{t("account.or")}</p>
          <form onSubmit={onEmail} className="stack-sm">
            <label htmlFor="signin-email" className="label">
              {t("account.emailLabel")}
            </label>
            <input id="signin-email" type="email" inputMode="email" autoComplete="email" enterKeyHint="send" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button type="submit" className="btn btn-primary btn-block" disabled={busy || !email.trim()}>
              {t("account.sendLink")}
            </button>
          </form>
        </div>
      )}
      <p role="status" className="small">
        {message}
      </p>
      {statsToggle}
      <p className="muted small">{t("account.statsNote")}</p>
    </section>
  );
}
