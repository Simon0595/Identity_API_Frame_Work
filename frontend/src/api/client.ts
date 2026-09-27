/** Shared fetch wrapper: Bearer header plus 401/403/404/429 mapping. */

import { getApiBaseUrl } from "../config";
import { getAccessToken } from "../auth/token";

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function joinUrl(path: string): string {
  const base = getApiBaseUrl();
  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
}

/** Authenticated JSON fetch; throws ApiError on non-2xx responses. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(joinUrl(path), { ...options, headers });

  if (!response.ok) {
    let body: unknown = null;
    const text = await response.text();
    if (text) {
      try {
        body = JSON.parse(text) as unknown;
      } catch {
        body = text;
      }
    }
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
