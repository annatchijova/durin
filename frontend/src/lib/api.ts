// Server-only client for api_server.py. Never imported from a "use client"
// component directly -- pages fetch here in Server Components, and the
// handful of mutating actions go through src/app/api/* Route Handlers so
// the browser only ever talks to this Next.js server, never to the Python
// API's host/port directly.

import type { Case, CaseSummary, ChatResponse } from "./types";
import { demoEnabled, demoGetCase, demoListCases } from "./demo";

const API_BASE = process.env.DURIN_API_URL ?? "http://127.0.0.1:8010";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Recorded demo (see lib/demo.ts): reads come from the snapshot, writes are refused.
  if (demoEnabled()) throw new ApiError(503, "Recorded demo: this action needs a live api_server.py and runs in the video, not here.");
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    // ngrok-skip-browser-warning: harmless against a real deployment, but
    // required when DURIN_API_URL points at an ngrok tunnel (used for a
    // provisional preview before a real backend host is set up) -- without
    // it, ngrok's free tier can serve an HTML interstitial instead of JSON.
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const raw = await response.text();
    // FastAPI's HTTPException body is {"detail": "..."}; surface that
    // message cleanly instead of the raw JSON text.
    let message = raw || response.statusText;
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // not JSON -- use the raw text as-is
    }
    throw new ApiError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export async function listCases(): Promise<{ cases: CaseSummary[] }> {
  if (demoEnabled()) return { cases: demoListCases() };
  return request("/api/cases");
}

export async function getCase(reportId: string): Promise<Case> {
  if (demoEnabled()) {
    const found = demoGetCase(reportId);
    if (!found) throw new ApiError(404, `case not found: ${reportId}`);
    return found;
  }
  return request(`/api/cases/${encodeURIComponent(reportId)}`);
}

export function runPipeline(sourceDir?: string): Promise<Case> {
  return request("/api/pipeline/run", { method: "POST", body: JSON.stringify({ sourceDir }) });
}

export function createProposal(reportId: string): Promise<Case> {
  return request(`/api/cases/${encodeURIComponent(reportId)}/proposal`, { method: "POST" });
}

export function approveProposal(reportId: string, approverId: string): Promise<Case> {
  return request(`/api/cases/${encodeURIComponent(reportId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ approverId }),
  });
}

export function submitToPaypal(reportId: string): Promise<Case> {
  return request(`/api/cases/${encodeURIComponent(reportId)}/submit`, { method: "POST" });
}

export function refreshPayout(reportId: string): Promise<Case> {
  return request(`/api/cases/${encodeURIComponent(reportId)}/refresh-payout`, { method: "POST" });
}

export function askChat(question: string): Promise<ChatResponse> {
  return request("/api/chat", { method: "POST", body: JSON.stringify({ question }) });
}

export { ApiError };
