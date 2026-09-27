/**
 * Cognito env validation - config must fail fast when pool settings are missing.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

describe("requireCognitoEnv", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("returns trimmed Cognito settings when all vars are set", async () => {
    vi.stubEnv("VITE_COGNITO_AUTHORITY", " https://cognito-idp.eu-west-1.amazonaws.com/pool ");
    vi.stubEnv("VITE_COGNITO_CLIENT_ID", " abc123 ");
    vi.stubEnv("VITE_COGNITO_REDIRECT_URI", " http://localhost:5173/callback ");
    const { requireCognitoEnv } = await import("./cognitoConfig");
    expect(requireCognitoEnv()).toEqual({
      authority: "https://cognito-idp.eu-west-1.amazonaws.com/pool",
      clientId: "abc123",
      redirectUri: "http://localhost:5173/callback",
    });
  });

  it("throws when any Cognito env var is missing", async () => {
    vi.stubEnv("VITE_COGNITO_AUTHORITY", "https://example.com/pool");
    vi.stubEnv("VITE_COGNITO_CLIENT_ID", "");
    vi.stubEnv("VITE_COGNITO_REDIRECT_URI", "http://localhost:5173/callback");
    const { requireCognitoEnv } = await import("./cognitoConfig");
    expect(() => requireCognitoEnv()).toThrow(/VITE_COGNITO/);
  });
});
