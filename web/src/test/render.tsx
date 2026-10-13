import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { I18nProvider, type Lang } from "../i18n";

export function renderWith(ui: ReactElement, lang: Lang = "en") {
  return render(
    <I18nProvider initial={lang}>
      <MemoryRouter>{ui}</MemoryRouter>
    </I18nProvider>,
  );
}
