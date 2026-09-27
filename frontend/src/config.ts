/** Vite env. No secrets here; the Cognito client id is public. */

export type AuthMode = "dev" | "cognito";

/** Backend origin without trailing slash (e.g. http://127.0.0.1:8000). */
export function getApiBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!base) {
    throw new Error("VITE_API_BASE_URL is required");
  }
  return base.replace(/\/$/, "");
}

/** Offline dev login vs Cognito Hosted UI - selected at build time via env. */
export function getAuthMode(): AuthMode {
  const mode = import.meta.env.VITE_AUTH_MODE;
  if (mode === "cognito") {
    return "cognito";
  }
  if (mode === "dev") {
    return "dev";
  }
  throw new Error('VITE_AUTH_MODE must be "dev" or "cognito"');
}
