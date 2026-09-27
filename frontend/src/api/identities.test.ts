/**
 * Identity read API tests - mock fetch; proves context query is wired correctly.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEMO_PERSON_ID, fetchIdentity } from "./identities";

describe("fetchIdentity", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("requests the identity read path with the context query param", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          person_id: DEMO_PERSON_ID,
          context: "professional",
          fields: { given_name: "Jordan" },
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const body = await fetchIdentity(DEMO_PERSON_ID, "professional");

    expect(body.fields.given_name).toBe("Jordan");
    expect(fetchMock.mock.calls[0][0]).toBe(
      `http://api.test/api/v1/identities/${DEMO_PERSON_ID}?context=professional`,
    );
  });
});
