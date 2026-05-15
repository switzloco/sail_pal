const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window !== "undefined") {
    // Mirror lib/api.ts: in the Tauri shell, target the sidecar directly.
    if ("__TAURI_INTERNALS__" in window) {
      return "http://127.0.0.1:8000";
    }
    return window.location.origin;
  }
  return "http://localhost:8000";
};

const API_BASE = getApiBase() + "/api";

export interface SetupStatus {
  ollama_installed: boolean;
  ollama_running: boolean;
  model_ready: boolean;
  model_name: string;
  install_url: string;
  mode: "local" | "cloud";
  data_dir: string;
  server_is_local: boolean;
}


export async function fetchSetupStatus(): Promise<SetupStatus> {
  const res = await fetch(`${API_BASE}/setup/status`, {
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export interface PullProgress {
  status: string;
  digest?: string;
  total?: number;
  completed?: number;
  done?: boolean;
}

export async function fetchMode(): Promise<"cloud" | "local"> {
  const res = await fetch(`${API_BASE}/setup/mode`, {
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error("Could not fetch mode");
  const data = await res.json();
  return data.mode;
}

export async function setMode(mode: "cloud" | "local"): Promise<void> {
  const res = await fetch(`${API_BASE}/setup/mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Switch failed" }));
    throw new Error(err.detail ?? "Switch failed");
  }
}

export function streamModelPull(
  onProgress: (p: PullProgress) => void,
  onDone: (success: boolean) => void,
): () => void {
  const ctrl = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/setup/pull-model`, {
        method: "POST",
        signal: ctrl.signal,
      });
      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const obj: PullProgress = JSON.parse(line.slice(6));
            onProgress(obj);
            if (obj.done) {
              onDone(obj.status === "success");
              return;
            }
          } catch {
            // malformed line — skip
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onDone(false);
      }
    }
  })();

  return () => ctrl.abort();
}
