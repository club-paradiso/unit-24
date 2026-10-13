import { useT } from "../i18n";

/** Account and sync settings. Replaced by the Firebase-backed version once configured. */
export function AccountSection() {
  const t = useT();
  return (
    <section className="stack-sm" aria-labelledby="account-h">
      <h2 id="account-h">{t("account.title")}</h2>
      <p className="muted small">{t("account.unavailable")}</p>
    </section>
  );
}
