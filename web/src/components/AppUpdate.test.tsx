import { act, render, screen } from '@testing-library/react';
import { I18nProvider } from '../i18n';
import { AppUpdate } from './AppUpdate';

const original = Object.getOwnPropertyDescriptor(navigator, 'serviceWorker');
afterEach(() => {
  vi.unstubAllEnvs();
  if (original) Object.defineProperty(navigator, 'serviceWorker', original);
  else Reflect.deleteProperty(navigator, 'serviceWorker');
});

async function setup(controlled: boolean) {
  vi.stubEnv('PROD', true);
  const worker = Object.assign(new EventTarget(), { state: 'installed', postMessage: vi.fn() });
  const registration = Object.assign(new EventTarget(), { waiting: worker, installing: worker, update: vi.fn(async () => {}) });
  const sw = Object.assign(new EventTarget(), { controller: controlled ? {} : null, register: vi.fn(async () => registration) });
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: sw });
  await act(async () => { render(<I18nProvider initial="en"><AppUpdate /></I18nProvider>); });
  return { worker, registration };
}

it('does not mistake first installation for a waiting update', async () => {
  await setup(false);
  expect(screen.queryByRole('status')).toBeNull();
});

it('offers a genuinely waiting update on an already-controlled page', async () => {
  await setup(true);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

it('clears the prompt if another tab activates the waiting worker', async () => {
  const { worker, registration } = await setup(true);
  act(() => registration.dispatchEvent(new Event('updatefound')));
  act(() => { worker.state = 'activated'; worker.dispatchEvent(new Event('statechange')); });
  expect(screen.queryByRole('status')).toBeNull();
});
