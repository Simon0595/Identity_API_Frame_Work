/** Protected dashboard: header and the role-gated demo widgets. */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchMe, type MeResponse } from "../../api/me";
import { NON_OWNER_SUB } from "../../auth/devLogin";
import { clearAccessToken } from "../../auth/token";
import { BRAND_NAME } from "../../brand";
import { formatError } from "./formatError";
import styles from "./AppShell.module.css";
import { AuditWidget } from "./widgets/AuditWidget";
import { RedactionWidget } from "./widgets/RedactionWidget";
import { SessionWidget } from "./widgets/SessionWidget";
import { WriteWidget } from "./widgets/WriteWidget";

export function AppShell() {
  const navigate = useNavigate();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchMe()
      .then((identity) => {
        if (!cancelled) {
          setMe(identity);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          clearAccessToken();
          setError(formatError(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleLogout() {
    clearAccessToken();
    navigate("/", { replace: true });
  }

  if (error) {
    return (
      <main className={styles.shell}>
        <p role="alert" className={styles.error}>
          {error}
        </p>
      </main>
    );
  }

  if (!me) {
    return (
      <main className={styles.shell}>
        <p className={styles.loading}>Loading session…</p>
      </main>
    );
  }

  const isOwnerSubject = me.role === "subject" && me.sub !== NON_OWNER_SUB;

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.brand}>{BRAND_NAME}</h1>
        <span className={styles.badge} aria-label={`Role: ${me.role}`}>
          {me.role}
        </span>
      </header>

      <SessionWidget me={me} onLogout={handleLogout} />
      <RedactionWidget me={me} />
      {isOwnerSubject && <WriteWidget />}
      {me.role === "admin" && <AuditWidget />}
    </main>
  );
}
