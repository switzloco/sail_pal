"use client";

import { apiFetch } from "./api";

export interface QueuedRequest {
  id: string;
  path: string;
  method: string;
  body: string;
  timestamp: number;
}

const QUEUE_KEY = "vessel_ops_sync_queue";

export function getQueue(): QueuedRequest[] {
  if (typeof window === "undefined") return [];
  const raw = localStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export function addToQueue(path: string, method: string, body: any) {
  const queue = getQueue();
  const req: QueuedRequest = {
    id: crypto.randomUUID(),
    path,
    method,
    body: JSON.stringify(body),
    timestamp: Date.now(),
  };
  queue.push(req);
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  return req.id;
}

export async function processQueue(): Promise<number> {
  const queue = getQueue();
  if (queue.length === 0) return 0;

  const remaining: QueuedRequest[] = [];
  let processed = 0;

  for (const req of queue) {
    try {
      await apiFetch(req.path, {
        method: req.method,
        body: req.body,
      });
      processed++;
    } catch (err) {
      console.warn(`Sync failed for ${req.id}, keeping in queue:`, err);
      remaining.push(req);
    }
  }

  localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
  return processed;
}
