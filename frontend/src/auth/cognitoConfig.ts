/** Cognito Hosted UI settings (authorization code + PKCE). */

import {
  InMemoryWebStorage,
  WebStorageStateStore,
  type UserManagerSettings,
} from "oidc-client-ts";

export interface CognitoEnv {
  authority: string;
  clientId: string;
  redirectUri: string;
}

/** Required VITE_COGNITO_* values when VITE_AUTH_MODE=cognito. */
export function requireCognitoEnv(): CognitoEnv {
  const authority = import.meta.env.VITE_COGNITO_AUTHORITY?.trim();
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID?.trim();
  const redirectUri = import.meta.env.VITE_COGNITO_REDIRECT_URI?.trim();

  if (!authority || !clientId || !redirectUri) {
    throw new Error(
      "VITE_COGNITO_AUTHORITY, VITE_COGNITO_CLIENT_ID, and VITE_COGNITO_REDIRECT_URI are required when VITE_AUTH_MODE=cognito",
    );
  }

  return { authority, clientId, redirectUri };
}

/** Public app client - PKCE enabled by default; tokens not persisted to localStorage. */
export function buildCognitoOidcConfig(): UserManagerSettings {
  const { authority, clientId, redirectUri } = requireCognitoEnv();

  return {
    authority,
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    // Least privilege: the API derives role from the access-token `cognito:groups`
    // claim (see core/auth/cognito.py) and never reads profile/email, so request only
    // `openid`. Add `email`/`profile` here (and enable them on the app client) only if
    // the UI starts showing those claims.
    scope: "openid",
    automaticSilentRenew: false,
    // PKCE verifier must survive the Hosted UI redirect (sessionStorage only).
    stateStore: new WebStorageStateStore({ store: window.sessionStorage }),
    // Access token lives in React memory via OidcTokenSync - reload requires re-login.
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
  };
}
