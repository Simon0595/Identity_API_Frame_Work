/**
 * Identity write API tests - mock fetch; proves PUT path and body shape.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEMO_PERSON_ID } from "./identities";
import { writeIdentity } from "./identitiesWrite";

describe("writeIdentity", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("sends PUT with fields payload to the context write path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: DEMO_PERSON_ID,
          context: "professional",
          fields: { given_name: "Updated" },
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const body = await writeIdentity(DEMO_PERSON_ID, "professional", {
      given_name: "Updated",
    });

    expect(body.fields.given_name).toBe("Updated");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      `http://api.test/api/v1/identities/${DEMO_PERSON_ID}/contexts/professional`,
    );
    expect(init.method).toBe("PUT");
    expect(init.body).toBe(JSON.stringify({ fields: { given_name: "Updated" } }));
  });
});
