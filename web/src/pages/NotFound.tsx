import { Link } from "react-router";
import { useTitle } from "../state";

export function NotFound({ what = "page" }: { what?: string }) {
  useTitle("Not found");
  return (
    <div className="stack">
      <h1>That {what} does not exist</h1>
      <p>The link may be out of date, or the content may have been withdrawn after review.</p>
      <p>
        <Link to="/">Go to the start page</Link> or <Link to="/chp/reference">search the reference</Link>.
      </p>
    </div>
  );
}
