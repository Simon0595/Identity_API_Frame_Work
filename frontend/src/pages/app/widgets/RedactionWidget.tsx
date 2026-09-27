/**
 * Redaction demo - reads seeded identity with role/context-dependent field visibility.
 */

import { useState } from "react";
import {
  DEMO_PERSON_ID,
  fetchIdentity,
  type IdentityContext,
  type IdentityReadResponse,
} from "../../../api/identities";
import type { MeResponse } from "../../../api/me";
import { NON_OWNER_SUB } from "../../../auth/devLogin";
import { formatError } from "../formatError";
import styles from "./Widget.module.css";

const IDENTITY_CONTEXTS: IdentityContext[] = ["professional", "personal"];

interface RedactionWidgetProps {
  me: MeResponse;
}

export function RedactionWidget({ me }: RedactionWidgetProps) {
  const [identityRead, setIdentityRead] = useState<IdentityReadResponse | null>(
    null,
  );
  const [identityError, setIdentityError] = useState<string | null>(null);
  const [identityLoading, setIdentityLoading] = useState(false);

  async function handleIdentityRead(context: IdentityContext) {
    setIdentityError(null);
    setIdentityRead(null);
    setIdentityLoading(true);
    try {
      setIdentityRead(await fetchIdentity(DEMO_PERSON_ID, context));
    } catch (err) {
      setIdentityError(formatError(err));
    } finally {
      setIdentityLoading(false);
    }
  }

  return (
    <section className={styles.widget} aria-labelledby="redaction-heading">
      <h2 id="redaction-heading" className={styles.title}>
        Redaction demo
      </h2>
      <p className={styles.hint}>
        Same seeded person ({DEMO_PERSON_ID}). Which fields you see depends on
        your role and the context.
      </p>
      {me.role === "subject" && me.sub === NON_OWNER_SUB && (
        <p className={styles.hint}>
          Subject tokens only work on your own record. Reading someone else
          returns <strong>404</strong>, not 403.
        </p>
      )}
      <div className={styles.buttonRow}>
        {IDENTITY_CONTEXTS.map((context) => (
          <button
            key={context}
            type="button"
            className={styles.button}
            disabled={identityLoading}
            onClick={() => void handleIdentityRead(context)}
          >
            Read {context}
          </button>
        ))}
      </div>
      {identityError && (
        <p role="alert" className={styles.error}>
          {identityError}
        </p>
      )}
      {identityRead && (
        <pre className={styles.pre}>{JSON.stringify(identityRead, null, 2)}</pre>
      )}
    </section>
  );
}
