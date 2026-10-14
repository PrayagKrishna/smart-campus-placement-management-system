/** Thin fetch wrapper. Every page talks to the backend through this. */

export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export class ApiError extends Error {
  status: number;
  reasons: string[];
  constructor(status: number, message: string, reasons: string[] = []) {
    super(message);
    this.status = status;
    this.reasons = reasons;
  }
}

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const body = text ? JSON.parse(text) : null;

  if (!response.ok) {
    // FastAPI validation errors arrive as a list under `detail`.
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: { loc?: string[]; msg: string }) => `${d.loc?.slice(1).join(".") ?? "field"}: ${d.msg}`).join("; ")
      : typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message, body?.reasons ?? []);
  }
  return body as T;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};

/** Build a query string, dropping empty values so filters stay optional. */
export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const out = search.toString();
  return out ? `?${out}` : "";
}

export const fmtCtc = (v: string | number | null | undefined) =>
  v === null || v === undefined ? "—" : `₹${Number(v).toFixed(2)} LPA`;

export const fmtDate = (v: string | null | undefined) =>
  v ? new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const fmtDateTime = (v: string | null | undefined) =>
  v
    ? new Date(v).toLocaleString("en-IN", {
        day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
      })
    : "—";

export const fullName = (first?: string | null, last?: string | null) =>
  [first, last].filter(Boolean).join(" ") || "—";
