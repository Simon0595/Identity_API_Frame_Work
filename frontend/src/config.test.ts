/**
 * Auth-mode config tests - env switch must pick dev vs cognito at build time.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

describe("getAuthMode", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('returns "dev" when VITE_AUTH_MODE=dev', async () => {
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    const { getAuthMode } = await import("./config");
    expect(getAuthMode()).toBe("dev");
  });

  it('returns "cognito" when VITE_AUTH_MODE=cognito', async () => {
    vi.stubEnv("VITE_AUTH_MODE", "cognito");
    const { getAuthMode } = await import("./config");
    expect(getAuthMode()).toBe("cognito");
  });

  it("throws on an unknown auth mode", async () => {
    vi.stubEnv("VITE_AUTH_MODE", "oauth1");
    const { getAuthMode } = await import("./config");
    expect(() => getAuthMode()).toThrow(/VITE_AUTH_MODE/);
  });
});
