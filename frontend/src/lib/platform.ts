/**
 * Platform detection + Tauri IPC helpers.
 *
 * Tauri 2 injects `__TAURI_INTERNALS__` on window during webview init.
 * That object exposes `invoke()`, so we don't need the `@tauri-apps/api`
 * npm package for our handful of IPC calls.
 */

interface TauriInternals {
  invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
}

function tauriInternals(): TauriInternals | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { __TAURI_INTERNALS__?: TauriInternals };
  return w.__TAURI_INTERNALS__ ?? null;
}

export function isTauri(): boolean {
  return tauriInternals() !== null;
}

/**
 * Invoke a Tauri Rust command. Throws if not running inside Tauri.
 */
export async function tauriInvoke<T = unknown>(
  cmd: string,
  args?: Record<string, unknown>
): Promise<T> {
  const internals = tauriInternals();
  if (!internals) {
    throw new Error(`tauriInvoke('${cmd}') called outside Tauri shell`);
  }
  return internals.invoke(cmd, args) as Promise<T>;
}
