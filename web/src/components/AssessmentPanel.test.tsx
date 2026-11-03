import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
vi.mock("../lib/audioWav", () => ({
  audioToWav16k: vi.fn(async () => new Blob(["wav"], { type: "audio/wav" })),
}));

/**
 * The panel caches its availability probe at module scope, so each test
 * imports a fresh copy of the component after stubbing fetch. The i18n
 * provider is imported from the same fresh module registry, otherwise its
 * context would not match the component's.
 */
async function renderPanel(fetchMock: ReturnType<typeof vi.fn>) {
  vi.resetModules();
  vi.stubGlobal("fetch", fetchMock);
  const { AssessmentPanel } = await import("./AssessmentPanel");
  const { I18nProvider } = await import("../i18n");
  const audio = new Blob(["recording"], { type: "audio/webm" });
  return render(
    <I18nProvider initial="en">
      <AssessmentPanel audio={audio} phrase="ten one" />
    </I18nProvider>,
  );
}

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });

describe("AssessmentPanel fail-soft behaviour", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("when assessment is not configured, explains that and shows no scores or analyse button", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ enabled: false, provider: "azure-pronunciation-assessment", maxSeconds: 20 }));
    await renderPanel(fetchMock);
    expect(await screen.findByText(/AI assessment isn't configured yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Assess pronunciation/ })).not.toBeInTheDocument();
    expect(screen.queryByText("Overall")).not.toBeInTheDocument();
  });

  it("when the status probe fails, treats assessment as unavailable instead of offering it", async () => {
    const fetchMock = vi.fn(async () => { throw new Error("offline"); });
    await renderPanel(fetchMock);
    expect(await screen.findByText(/AI assessment isn't configured yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Assess pronunciation/ })).not.toBeInTheDocument();
  });

  it("when enabled, requires explicit consent before analysing and surfaces a server outage plainly", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) =>
      init?.method === "POST"
        ? jsonResponse({ error: "ASSESSMENT_UNAVAILABLE" }, 503)
        : jsonResponse({ enabled: true, provider: "azure-pronunciation-assessment", maxSeconds: 20 }));
    await renderPanel(fetchMock);
    const analyze = await screen.findByRole("button", { name: /Assess pronunciation/ });
    expect(analyze).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(analyze).toBeEnabled();
    await userEvent.click(analyze);
    expect(await screen.findByRole("alert")).toHaveTextContent(/AI assessment is unavailable/);
    expect(screen.queryByText("Overall")).not.toBeInTheDocument();
  });
});
