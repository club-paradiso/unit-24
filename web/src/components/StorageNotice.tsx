import { useT } from "../i18n";
import { useStorageNotice, useStore } from "../state";

export function StorageNotice() {
  const t = useT();
  const notice = useStorageNotice();
  const store = useStore();
  if (!notice) return null;
  return (
    <div className="notice notice-warn" role="status">
      <p>{t(`storage.${notice}`)}</p>
      {notice === "corrupt" && (
        <button type="button" className="btn btn-small" onClick={() => store.dismissNotice()}>
          {t("common.dismiss")}
        </button>
      )}
    </div>
  );
}
