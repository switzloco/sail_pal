"use client";

import { useEffect, useState } from "react";
import { Anchor, LogIn, Loader2 } from "lucide-react";
import type { User } from "firebase/auth";
import {
  authConfigured,
  registerWithEmail,
  signInWithEmail,
  signInWithGoogle,
  watchAuth,
} from "@/lib/firebase";

/**
 * Blocks the app behind sign-in on the hosted deployment.
 *
 * Renders children untouched when Firebase config is absent, which is the
 * desktop build — that database lives on the user's own laptop and is already
 * scoped by physical access to it.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(authConfigured);

  useEffect(() => {
    if (!authConfigured) return;
    return watchAuth((u) => {
      setUser(u);
      setChecking(false);
    });
  }, []);

  if (!authConfigured) return <>{children}</>;

  if (checking) {
    return (
      <div className="min-h-screen bg-ocean-900 flex items-center justify-center">
        <Loader2 className="text-ocean-300 animate-spin" size={28} />
      </div>
    );
  }

  if (!user) return <SignInScreen />;
  return <>{children}</>;
}

function SignInScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? friendly(err.message) : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-ocean-900 text-white flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-white/10 p-2.5 rounded-xl">
            <Anchor size={22} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-ocean-400 leading-none mb-1">
              Vessel Ops AI
            </p>
            <h1 className="font-bold">Sign in to your vessel</h1>
          </div>
        </div>

        <p className="text-sm text-ocean-200 leading-relaxed mb-6">
          Your boat&apos;s records — crew, medical history, inventory — are private to
          your account. Sign in to keep them saved and reachable from any device.
        </p>

        <button
          onClick={() => run(signInWithGoogle)}
          disabled={busy}
          className="w-full flex items-center justify-center gap-2 bg-white text-slate-800 font-bold text-sm py-2.5 rounded-lg hover:bg-slate-100 disabled:opacity-60 transition-colors"
        >
          <LogIn size={16} /> Continue with Google
        </button>

        <div className="flex items-center gap-3 my-5 text-[10px] uppercase tracking-widest text-ocean-500">
          <span className="h-px bg-ocean-700 flex-1" /> or <span className="h-px bg-ocean-700 flex-1" />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(() =>
              mode === "signin"
                ? signInWithEmail(email, password)
                : registerWithEmail(email, password)
            );
          }}
          className="space-y-3"
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
            className="w-full bg-ocean-800 border border-ocean-700 rounded-lg px-3 py-2.5 text-sm placeholder:text-ocean-500 focus:outline-none focus:ring-2 focus:ring-ocean-500"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            required
            minLength={6}
            className="w-full bg-ocean-800 border border-ocean-700 rounded-lg px-3 py-2.5 text-sm placeholder:text-ocean-500 focus:outline-none focus:ring-2 focus:ring-ocean-500"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full bg-ocean-500 hover:bg-ocean-400 disabled:opacity-60 font-bold text-sm py-2.5 rounded-lg transition-colors"
          >
            {busy ? "…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        {error && (
          <p className="mt-4 text-xs text-red-300 bg-red-950/50 border border-red-900 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          onClick={() => {
            setMode(mode === "signin" ? "register" : "signin");
            setError(null);
          }}
          className="mt-5 text-xs text-ocean-300 hover:text-white transition-colors"
        >
          {mode === "signin"
            ? "No account yet? Create one"
            : "Already have an account? Sign in"}
        </button>

        <p className="mt-8 text-[11px] text-ocean-500 leading-relaxed">
          Running the desktop app instead? It keeps everything on your own machine
          and needs no account at all.
        </p>
      </div>
    </div>
  );
}

/** Firebase error codes are not something to show a skipper mid-passage. */
function friendly(message: string): string {
  if (message.includes("auth/invalid-credential") || message.includes("auth/wrong-password")) {
    return "That email and password don't match.";
  }
  if (message.includes("auth/email-already-in-use")) {
    return "There's already an account with that email — try signing in.";
  }
  if (message.includes("auth/weak-password")) {
    return "Password needs to be at least 6 characters.";
  }
  if (message.includes("auth/popup-closed-by-user")) {
    return "Sign-in window closed before finishing.";
  }
  if (message.includes("auth/network-request-failed")) {
    return "No connection. Sign-in needs internet — the desktop app doesn't.";
  }
  return message.replace(/^Firebase:\s*/, "");
}
