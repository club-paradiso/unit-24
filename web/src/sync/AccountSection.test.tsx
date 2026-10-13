import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { I18nProvider } from "../i18n";
import { ProgressStore, type KeyValueStorage, type ProgressState } from "../lib/progress";
import { ProgressProvider } from "../state";
import { AccountSection } from "./AccountSection";
import { SyncProvider, type Account, type AuthApi } from "./context";

class Mem implements KeyValueStorage {
  m = new Map<string, string>();
  getItem(k: string) {
    return this.m.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.m.set(k, v);
  }
  removeItem(k: string) {
    this.m.delete(k);
  }
}

function fakeApi() {
  // Like Firebase: a subscriber is told the current account at once, and again on every change.
  let current: Account | null = null;
  let listener: (a: Account | null) => void = () => {};
  const set = (a: Account | null) => {
    current = a;
    listener(a);
  };
  const cloud = new Map<string, ProgressState>();
  const api: AuthApi = {
    watchAccount: async (cb) => {
      listener = cb;
      cb(current);
      return () => {};
    },
    signInWithGoogle: vi.fn(async () => set({ uid: "u1", email: "learner@example.com", provider: "google.com" })),
    sendEmailLink: vi.fn(async () => {}),
    signOutAccount: vi.fn(async () => set(null)),
    deleteCloudProgress: vi.fn(async (uid: string) => void cloud.delete(uid)),
    backend: {
      pull: async (uid) => cloud.get(uid) ?? null,
      push: async (uid, s) => void cloud.set(uid, structuredClone(s)),
    },
  };
  return { api, cloud };
}

function setup() {
  const { api, cloud } = fakeApi();
  const store = new ProgressStore(new Mem());
  store.recordResults({ fct_a: true }, Date.UTC(2026, 9, 13));
  render(
    <I18nProvider initial="en">
      <ProgressProvider store={store}>
        <SyncProvider api={async () => api} configured>
          <MemoryRouter>
            <AccountSection />
          </MemoryRouter>
        </SyncProvider>
      </ProgressProvider>
    </I18nProvider>,
  );
  return { api, cloud, store };
}

it("signs in with Google, uploads this device's progress and can sign out", async () => {
  const { api, cloud } = setup();
  await userEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
  expect(api.signInWithGoogle).toHaveBeenCalledWith("en");
  await waitFor(() => expect(screen.getByText("Signed in as learner@example.com")).toBeInTheDocument());
  await waitFor(() => expect(screen.getByText(/^Synced ·/)).toBeInTheDocument());
  expect(cloud.get("u1")!.items.fct_a).toBeDefined();
  await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument());
});

it("sends an email sign-in link", async () => {
  const { api } = setup();
  await userEvent.type(screen.getByLabelText("Get a sign-in link by email"), "me@example.com");
  await userEvent.click(screen.getByRole("button", { name: "Send sign-in link" }));
  expect(api.sendEmailLink).toHaveBeenCalledWith("me@example.com", "en");
  expect(await screen.findByText(/We sent a sign-in link to me@example.com/)).toBeInTheDocument();
});

it("deletes the account copy only after confirmation", async () => {
  const { api, cloud } = setup();
  await userEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
  await waitFor(() => expect(cloud.has("u1")).toBe(true));
  await userEvent.click(screen.getByRole("button", { name: /Delete progress stored with your account/ }));
  await userEvent.click(screen.getByRole("button", { name: /Yes, delete it/ }));
  await waitFor(() => expect(api.deleteCloudProgress).toHaveBeenCalledWith("u1"));
  expect(cloud.has("u1")).toBe(false);
});
