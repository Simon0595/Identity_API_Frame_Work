/**
 * Public landing page. Edit this file to change the marketing copy.
 */

import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { fetchMe } from "../api/me";
import { CognitoLoginPanel } from "../auth/CognitoLoginPanel";
import { devLogin, NON_OWNER_SUB, type DevRole } from "../auth/devLogin";
import { clearAccessToken, getAccessToken } from "../auth/token";
import { BRAND_NAME } from "../brand";
import { getAuthMode } from "../config";
import styles from "./Landing.module.css";

const DEV_ROLES: DevRole[] = ["subject", "colleague", "admin"];

const FEATURES = [
  {
    title: "Role-based redaction",
    text: "Field visibility changes with role and declared context. Same record, different views.",
  },
  {
    title: "Ownership without disclosure",
    text: "Subjects who do not own a record receive 404, not 403, so existence is not leaked.",
  },
  {
    title: "Audit trail",
    text: "Admin-only access to recent identity changes; other roles are rejected at the API.",
  },
  {
    title: "Cognito-ready",
    text: "Hosted UI with Authorization Code + PKCE; bearer token kept in memory only.",
  },
] as const;

function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    return `Request failed (${err.status})`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Request failed";
}

export function Landing() {
  const navigate = useNavigate();
  const authMode = getAuthMode();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (getAccessToken()) {
    return <Navigate to="/app" replace />;
  }

  async function handleDevLogin(role: DevRole, sub?: string) {
    setError(null);
    setLoading(true);
    try {
      await devLogin(role, sub !== undefined ? { sub } : {});
      await fetchMe();
      navigate("/app");
    } catch (err) {
      clearAccessToken();
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  }

  function handleSession() {
    navigate("/app");
  }

  return (
    <main className={styles.landing}>
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>{BRAND_NAME}</h1>
        <p className={styles.heroLead}>
          A secure API template with role-aware identity access, audit logging, and
          production-ready Cognito integration.
        </p>
      </section>

      <div className={styles.features}>
        {FEATURES.map((feature) => (
          <article key={feature.title} className={styles.feature}>
            <h2 className={styles.featureTitle}>{feature.title}</h2>
            <p className={styles.featureText}>{feature.text}</p>
          </article>
        ))}
      </div>

      <section className={styles.cta} aria-labelledby="sign-in-heading">
        <h2 id="sign-in-heading" className={styles.ctaTitle}>
          Sign in
        </h2>
        <p className={styles.ctaHint}>
          {authMode === "dev"
            ? "Choose a demo role. Uses POST /api/v1/dev/login (offline only)."
            : "Hosted UI redirect. Token stays in memory; reload requires re-login."}
        </p>

        {authMode === "dev" && (
          <div className={styles.buttonRow}>
            {DEV_ROLES.map((role) => (
              <button
                key={role}
                type="button"
                className={styles.primaryButton}
                disabled={loading}
                onClick={() => void handleDevLogin(role)}
              >
                Log in as {role}
              </button>
            ))}
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={loading}
              onClick={() => void handleDevLogin("subject", NON_OWNER_SUB)}
            >
              Log in as subject (non-owner)
            </button>
          </div>
        )}

        {authMode === "cognito" && (
          <CognitoLoginPanel
            onSession={handleSession}
            onError={(message) => {
              clearAccessToken();
              setError(message);
            }}
          />
        )}

        {error && (
          <p role="alert" className={styles.error}>
            {error}
          </p>
        )}
      </section>
    </main>
  );
}
