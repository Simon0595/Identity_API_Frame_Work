/**
 * Cognito login controls - Hosted UI redirect and session bootstrap via GET /api/v1/me.
 */

import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import { fetchMe, type MeResponse } from "../api/me";
import { ApiError } from "../api/client";
import { clearAccessToken, setAccessToken } from "./token";

interface CognitoLoginPanelProps {
  onSession: (me: MeResponse) => void;
  onError: (message: string) => void;
}

function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    return `Request failed (${err.status})`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Request failed";
}

export function CognitoLoginPanel({ onSession, onError }: CognitoLoginPanelProps) {
  const auth = useAuth();

  useEffect(() => {
    if (!auth.isAuthenticated || !auth.user?.access_token) {
      return;
    }
    // Populate the in-memory bearer BEFORE the first API call. OidcTokenSync also
    // mirrors it, but that lives in a parent component and React runs child effects
    // before parent effects - so without this, the first fetchMe would send no
    // Authorization header and get a 401 ("credentials were not provided").
    setAccessToken(auth.user.access_token);
    let cancelled = false;
    void fetchMe()
      .then((me) => {
        if (!cancelled) {
          onSession(me);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          clearAccessToken();
          onError(formatError(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [auth.isAuthenticated, auth.user?.access_token, onSession, onError]);

  if (auth.isLoading || auth.activeNavigator === "signinRedirect") {
    return <p>Signing in…</p>;
  }

  if (auth.isAuthenticated) {
    return null;
  }

  if (auth.error) {
    // The provider has already stripped any stale ?code&state, so a fresh redirect
    // starts a clean flow - surface the error but still let the user retry.
    return (
      <div>
        <p role="alert" className="error">
          Cognito sign-in failed: {auth.error.message}
        </p>
        <button type="button" onClick={() => void auth.signinRedirect()}>
          Try signing in again
        </button>
      </div>
    );
  }

  return (
    <button type="button" onClick={() => void auth.signinRedirect()}>
      Sign in with Cognito
    </button>
  );
}

export function CognitoLogoutButton({
  onLoggedOut,
}: {
  onLoggedOut: () => void;
}) {
  const auth = useAuth();

  return (
    <button
      type="button"
      onClick={() => {
        clearAccessToken();
        onLoggedOut();
        void auth.removeUser();
      }}
    >
      Log out
    </button>
  );
}
