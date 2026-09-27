/**
 * GET /api/v1/me - caller identity from the validated JWT (no DB lookup).
 */

import { apiFetch } from "./client";

export interface MeResponse {
  sub: string;
  role: string;
}

export async function fetchMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/v1/me");
}
