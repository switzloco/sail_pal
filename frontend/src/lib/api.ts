const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:8000";
};

const API_BASE = getApiBase() + "/api";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

/** Ping the backend — resolves true if reachable, false otherwise. */
export async function pingBackend(): Promise<boolean> {
  try {
    const baseUrl = getApiBase();
    const url = `${baseUrl.replace(/\/$/, "")}/healthz`;
    const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch (err) {
    console.warn("Heartbeat failed:", err);
    return false;
  }
}
