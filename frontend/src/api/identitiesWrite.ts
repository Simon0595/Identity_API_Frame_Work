/**
 * PUT /api/v1/identities/{person_id}/contexts/{context} - write path with mass-assignment guard.
 */

import { apiFetch } from "./client";
import type { IdentityContext } from "./identities";

export interface IdentityWriteResponse {
  id: string;
  context: string;
  fields: Record<string, string>;
}

/** Update writable profile fields; server rejects keys outside the role/context allow-list. */
export async function writeIdentity(
  personId: string,
  context: IdentityContext,
  fields: Record<string, string>,
): Promise<IdentityWriteResponse> {
  return apiFetch<IdentityWriteResponse>(
    `/api/v1/identities/${personId}/contexts/${context}`,
    {
      method: "PUT",
      body: JSON.stringify({ fields }),
    },
  );
}
