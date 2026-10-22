import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { I18nProvider } from "../i18n";
import { SpeechCoach } from "./SpeechCoach";

describe("speech coach graceful fallback", () => {
  afterEach(() => vi.restoreAllMocks());
  it("renders listen controls and a clear fallback without requiring a microphone", () => {
    render(<I18nProvider initial="en"><SpeechCoach phrase="ten four" /></I18nProvider>);
    expect(screen.getByRole("button", { name: /Hear pronunciation/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Hear slowly/ })).toBeInTheDocument();
    expect(screen.getByText("ten four")).toBeInTheDocument();
    expect(screen.getByText(/Speech recognition is unavailable here/)).toBeInTheDocument();
  });
  it("uses Korean instructions when requested", () => {
    render(<I18nProvider initial="ko"><SpeechCoach phrase="ten one" compact /></I18nProvider>);
    expect(screen.getByRole("button", { name: /발음 듣기/ })).toBeInTheDocument();
  });
});
