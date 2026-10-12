import { useStorageNotice, useStore } from "../state";

const TEXT = {
  unavailable: "Your browser is not letting this site save data, so progress will be lost when you close the tab.",
  corrupt: "Saved progress could not be read and has been reset. A copy of the unreadable data was kept in this browser.",
  "write-failed": "Your latest progress could not be saved (storage may be full). It is kept until you close the tab.",
} as const;

export function StorageNotice() {
  const notice = useStorageNotice();
  const store = useStore();
  if (!notice) return null;
  return (
    <div className="notice notice-warn" role="status">
      <p>{TEXT[notice]}</p>
      {notice === "corrupt" && (
        <button type="button" className="btn btn-small" onClick={() => store.dismissNotice()}>
          Dismiss
        </button>
      )}
    </div>
  );
}
