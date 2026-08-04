/**
 * Firebase Auth — hosted deployment only.
 *
 * The desktop build never touches this: its database is a SQLite file on the
 * user's own laptop, so a login would add friction at sea and protect nothing.
 * The hosted app is on the public internet holding real crew medical records,
 * so it requires a signed-in user for every data route.
 *
 * Config comes from NEXT_PUBLIC_FIREBASE_* at build time. These values are not
 * secrets — Firebase web config is public by design, and access is enforced by
 * the backend against each vessel's membership. If they are unset the app runs
 * unauthenticated, which is exactly what the desktop build wants.
 */
import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import {
  GoogleAuthProvider,
  browserLocalPersistence,
  getAuth,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
  createUserWithEmailAndPassword,
  signOut as fbSignOut,
  type Auth,
  type User,
} from "firebase/auth";

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

/** True when this build was given Firebase credentials to sign in against. */
export const authConfigured = Boolean(config.apiKey && config.authDomain && config.projectId);

let app: FirebaseApp | null = null;
let authInstance: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (!authConfigured || typeof window === "undefined") return null;
  if (!authInstance) {
    app = getApps().length ? getApps()[0] : initializeApp(config as Record<string, string>);
    authInstance = getAuth(app);
    // Survive the app being backgrounded — a phone in a pocket at sea should
    // not be signed out by the time it comes back out.
    setPersistence(authInstance, browserLocalPersistence).catch(() => {});
  }
  return authInstance;
}

export function watchAuth(cb: (user: User | null) => void): () => void {
  const auth = getFirebaseAuth();
  if (!auth) {
    cb(null);
    return () => {};
  }
  return onAuthStateChanged(auth, cb);
}

export async function signInWithGoogle(): Promise<void> {
  const auth = getFirebaseAuth();
  if (!auth) throw new Error("Sign-in is not configured for this build.");
  await signInWithPopup(auth, new GoogleAuthProvider());
}

export async function signInWithEmail(email: string, password: string): Promise<void> {
  const auth = getFirebaseAuth();
  if (!auth) throw new Error("Sign-in is not configured for this build.");
  await signInWithEmailAndPassword(auth, email, password);
}

export async function registerWithEmail(email: string, password: string): Promise<void> {
  const auth = getFirebaseAuth();
  if (!auth) throw new Error("Sign-in is not configured for this build.");
  await createUserWithEmailAndPassword(auth, email, password);
}

export async function signOut(): Promise<void> {
  const auth = getFirebaseAuth();
  if (auth) await fbSignOut(auth);
}

/**
 * Current ID token, or null when signed out / not configured.
 *
 * The Firebase SDK caches this and refreshes it when it is close to expiring,
 * so calling it per request is cheap and avoids sending a stale token after the
 * app has been backgrounded for an hour.
 */
export async function getIdToken(): Promise<string | null> {
  const auth = getFirebaseAuth();
  const user = auth?.currentUser;
  if (!user) return null;
  try {
    return await user.getIdToken();
  } catch {
    return null;
  }
}
