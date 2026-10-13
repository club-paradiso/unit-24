import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { I18nProvider } from "./i18n";
import { ProgressProvider } from "./state";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing from index.html");

createRoot(root).render(
  <StrictMode>
    <ErrorBoundary>
      <I18nProvider>
        <ProgressProvider>
          <App />
        </ProgressProvider>
      </I18nProvider>
    </ErrorBoundary>
  </StrictMode>,
);
