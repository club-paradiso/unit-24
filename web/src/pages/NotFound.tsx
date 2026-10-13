import { Link } from "react-router";
import { useT } from "../i18n";
import { useTitle } from "../state";

export function NotFound({ what = "page" }: { what?: "page" | "lesson" | "entry" }) {
  const t = useT();
  useTitle(t("notFound.short"));
  return (
    <div className="stack">
      <h1>{t(`notFound.${what}`)}</h1>
      <p>{t("notFound.text")}</p>
      <p>
        <Link to="/">{t("notFound.home")}</Link> · <Link to="/chp/reference">{t("notFound.search")}</Link>
      </p>
    </div>
  );
}
