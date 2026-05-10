const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:8000";
};

const API_BASE = getApiBase() + "/api";

export const getUploadUrl = (path: string) => {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${getApiBase()}/uploads/${path}`;
};

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...init?.headers } as Record<string, string>;
  
  if (!(init?.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

let failureCount = 0;

/** Ping the backend — resolves true if reachable, false otherwise. */
export async function pingBackend(): Promise<boolean> {
  try {
    const baseUrl = getApiBase();
    const url = `${baseUrl.replace(/\/$/, "")}/healthz`;
    // Increase timeout to 10s to handle Cloud Run cold starts
    const res = await fetch(url, { signal: AbortSignal.timeout(10000) });
    if (res.ok) {
      failureCount = 0;
      return true;
    }
    throw new Error("Ping non-OK");
  } catch (err) {
    failureCount++;
    console.warn(`Heartbeat attempt ${failureCount} failed:`, err);
    // Only report "down" if it fails twice in a row (stops flickering)
    return failureCount < 2;
  }
}

