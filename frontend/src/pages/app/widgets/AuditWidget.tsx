/** Audit trail demo. The API still returns 403 for non-admin callers. */

import { useState } from "react";
import { fetchAuditTrail, type AuditEntry } from "../../../api/audit";
import { DEMO_PERSON_ID } from "../../../api/identities";
import { formatError } from "../formatError";
import styles from "./Widget.module.css";

export function AuditWidget() {
  const [auditEntries, setAuditEntries] = useState<AuditEntry[] | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  async function handleAuditFetch() {
    setAuditError(null);
    setAuditEntries(null);
    setAuditLoading(true);
    try {
      setAuditEntries(await fetchAuditTrail(DEMO_PERSON_ID));
    } catch (err) {
      setAuditError(formatError(err));
    } finally {
      setAuditLoading(false);
    }
  }

  return (
    <section className={styles.widget} aria-labelledby="audit-heading">
      <h2 id="audit-heading" className={styles.title}>
        Audit trail
      </h2>
      <p className={styles.hint}>
        GET /api/v1/identities/.../audit is admin-only. Other roles get{" "}
        <strong>403</strong>.
      </p>
      <button
        type="button"
        className={styles.button}
        disabled={auditLoading}
        onClick={() => void handleAuditFetch()}
      >
        Fetch audit trail
      </button>
      {auditError && (
        <p role="alert" className={styles.error}>
          {auditError}
        </p>
      )}
      {auditEntries && (
        <pre className={styles.pre}>{JSON.stringify(auditEntries, null, 2)}</pre>
      )}
    </section>
  );
}
