/**
 * Dev login unit tests - mock fetch; verifies POST body and in-memory token storage.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAccessToken, getAccessToken } from "./token";

describe("devLogin", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
    clearAccessToken();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    clearAccessToken();
  });

  it("POSTs role to dev/login and stores the access token in memory", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "minted-jwt", token_type: "Bearer" }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { devLogin } = await import("./devLogin");
    await devLogin("colleague");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/api/v1/dev/login");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ role: "colleague" }));
    expect(getAccessToken()).toBe("minted-jwt");
  });

  it("includes sub in the POST body when provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "other-jwt", token_type: "Bearer" }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const { devLogin, NON_OWNER_SUB } = await import("./devLogin");
    await devLogin("subject", { sub: NON_OWNER_SUB });

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(
      JSON.stringify({ role: "subject", sub: NON_OWNER_SUB }),
    );
    expect(getAccessToken()).toBe("other-jwt");
  });
});
