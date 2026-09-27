/**
 * Offline dev login - POST /api/v1/dev/login, store token in memory only.
 */

import { apiFetch } from "../api/client";
import { setAccessToken } from "./token";

/** Roles exposed by the backend dev-login allow-list. */
export type DevRole = "subject" | "colleague" | "admin";

/**
 * Subject sub that does NOT own the seeded fixture person - mirrors
 * tests/test_subject_ownership.py OTHER_SUB for the 404 walkthrough.
 */
export const NON_OWNER_SUB = "00000000-0000-4000-8000-0000000000ff";

interface DevLoginResponse {
  access_token: string;
  token_type: string;
}

export interface DevLoginOptions {
  /** Override JWT sub; default lets the backend pick the seed owner for subject demos. */
  sub?: string;
}

/** Mint a local JWT for the chosen role; replaces any prior in-memory token. */
export async function devLogin(
  role: DevRole,
  options: DevLoginOptions = {},
): Promise<void> {
  const body: { role: DevRole; sub?: string } = { role };
  if (options.sub !== undefined) {
    body.sub = options.sub;
  }
  const data = await apiFetch<DevLoginResponse>("/api/v1/dev/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
  setAccessToken(data.access_token);
}
