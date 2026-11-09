// Server-only client for api_server.py. Never imported from a "use client"
// component directly -- pages fetch here in Server Components, and the
// handful of mutating actions go through src/app/api/* Route Handlers so
// the browser only ever talks to this Next.js server, never to the Python
// API's host/port directly.

import type { Case, CaseSummary } from "./types";

const API_BASE = process.env.DURIN_API_URL ?? "http://127.0.0.1:8010";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  return response.json() as Promise<T>;
}

export function listCases(): Promise<{ cases: CaseSummary[] }> {
  return request("/api/cases");
}

export function getCase(reportId: string): Promise<Case> {
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

export { ApiError };
