/**
 * Audit trail API tests - mock fetch; no live backend or secrets.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEMO_PERSON_ID } from "./identities";
import { fetchAuditTrail } from "./audit";

describe("fetchAuditTrail", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("requests the admin audit list path for the given person", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            timestamp: "2026-01-01T00:00:00Z",
            caller_sub: "local|admin",
            role: "admin",
            action: "read",
            person_id: DEMO_PERSON_ID,
            context: "professional",
            fields_disclosed: ["given_name"],
            decision_reason: "policy_allowed",
          },
        ]),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const entries = await fetchAuditTrail(DEMO_PERSON_ID);

    expect(entries).toHaveLength(1);
    expect(entries[0].action).toBe("read");
    expect(fetchMock.mock.calls[0][0]).toBe(
      `http://api.test/api/v1/identities/${DEMO_PERSON_ID}/audit`,
    );
  });
});
