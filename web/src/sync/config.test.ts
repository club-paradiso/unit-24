import { readFirebaseConfig } from './config';
it('keeps missing and partial Firebase configuration disabled', () => {
  expect(readFirebaseConfig({})).toBeNull();
  expect(readFirebaseConfig({ VITE_FIREBASE_API_KEY: 'public-id' })).toBeNull();
});
it('accepts a complete public web configuration', () => {
  expect(readFirebaseConfig({ VITE_FIREBASE_API_KEY: 'public-id', VITE_FIREBASE_AUTH_DOMAIN: 'example.firebaseapp.com', VITE_FIREBASE_PROJECT_ID: 'example', VITE_FIREBASE_APP_ID: 'app' })).toMatchObject({ projectId: 'example' });
});
