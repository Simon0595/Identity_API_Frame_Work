/**
 * GET /api/v1/identities/{person_id}/audit. Admin only.
 */

import { apiFetch } from "./client";

export interface AuditEntry {
  timestamp: string;
  caller_sub: string;
  role: string;
  action: string;
  person_id: string;
  context: string | null;
  fields_disclosed: string[];
  decision_reason: string;
}

/** List recent audit rows for a person; non-admin callers receive 403 from the server. */
export async function fetchAuditTrail(
  personId: string,
): Promise<AuditEntry[]> {
  return apiFetch<AuditEntry[]>(`/api/v1/identities/${personId}/audit`);
}
