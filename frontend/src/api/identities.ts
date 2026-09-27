/**
 * GET /api/v1/identities/{person_id}?context=… - read path with role-based redaction.
 */

import { apiFetch } from "./client";

/** Seeded fixture person from `python manage.py seed` - synthetic, not real PII. */
export const DEMO_PERSON_ID = "11111111-1111-4111-8111-111111111111";

export type IdentityContext = "professional" | "personal";

export interface IdentityReadResponse {
  person_id: string;
  context: string;
  fields: Record<string, string>;
}

/** Read one identity in the declared context; server redacts fields by caller role. */
export async function fetchIdentity(
  personId: string,
  context: IdentityContext,
): Promise<IdentityReadResponse> {
  const query = new URLSearchParams({ context });
  return apiFetch<IdentityReadResponse>(
    `/api/v1/identities/${personId}?${query.toString()}`,
  );
}
