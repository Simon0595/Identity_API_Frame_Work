/**
 * API client unit tests - mock fetch; no live backend or secrets.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearAccessToken, setAccessToken } from "../auth/token";
import { ApiError, apiFetch } from "./client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
    clearAccessToken();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    clearAccessToken();
  });

  it("attaches Authorization Bearer when a token is set", async () => {
    setAccessToken("test-jwt");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/v1/me");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer test-jwt");
    expect(fetchMock.mock.calls[0][0]).toBe("http://api.test/api/v1/me");
  });

  it("omits Authorization when no token is set", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/health/");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it.each([401, 403, 404, 429])(
    "throws ApiError with status %i on error responses",
    async (status) => {
      const fetchMock = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "nope" }), { status }),
      );
      vi.stubGlobal("fetch", fetchMock);

      const err = await apiFetch("/api/v1/me").catch((e: unknown) => e);
      expect(err).toBeInstanceOf(ApiError);
      expect(err).toMatchObject({ status });
    },
  );
});
