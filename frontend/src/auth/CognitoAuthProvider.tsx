/**
 * Cognito Hosted UI wrapper - syncs OIDC access_token into in-memory bearer store.
 */

import { useEffect, type ReactNode } from "react";
import { AuthProvider, hasAuthParams, useAuth } from "react-oidc-context";
import { buildCognitoOidcConfig } from "./cognitoConfig";
import { clearAccessToken, setAccessToken } from "./token";

function OidcTokenSync({ children }: { children: ReactNode }) {
  const auth = useAuth();

  useEffect(() => {
    if (auth.isAuthenticated && auth.user?.access_token) {
      setAccessToken(auth.user.access_token);
      return;
    }
    if (!auth.isLoading && !auth.isAuthenticated) {
      clearAccessToken();
    }
  }, [auth.isAuthenticated, auth.isLoading, auth.user?.access_token]);

  // Failed Hosted UI returns leave ?code&state on the URL. Clear them so a
  // reload does not keep retrying a dead PKCE state.
  useEffect(() => {
    if (auth.error && hasAuthParams()) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [auth.error]);

  return children;
}

/** Strip OAuth query params after callback so refresh does not re-process the code. */
function onSigninCallback(): void {
  window.history.replaceState({}, document.title, window.location.pathname);
}

export function CognitoAuthProvider({ children }: { children: ReactNode }) {
  return (
    <AuthProvider {...buildCognitoOidcConfig()} onSigninCallback={onSigninCallback}>
      <OidcTokenSync>{children}</OidcTokenSync>
    </AuthProvider>
  );
}
