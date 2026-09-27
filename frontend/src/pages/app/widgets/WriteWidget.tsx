/** Write demo. The API still checks ownership even if this widget is shown. */

import { useState } from "react";
import { DEMO_PERSON_ID } from "../../../api/identities";
import {
  writeIdentity,
  type IdentityWriteResponse,
} from "../../../api/identitiesWrite";
import { formatError } from "../formatError";
import styles from "./Widget.module.css";

export function WriteWidget() {
  const [writeResult, setWriteResult] = useState<IdentityWriteResponse | null>(
    null,
  );
  const [writeError, setWriteError] = useState<string | null>(null);
  const [writeLoading, setWriteLoading] = useState(false);

  async function handleWrite(fields: Record<string, string>) {
    setWriteError(null);
    setWriteResult(null);
    setWriteLoading(true);
    try {
      setWriteResult(
        await writeIdentity(DEMO_PERSON_ID, "professional", fields),
      );
    } catch (err) {
      setWriteError(formatError(err));
    } finally {
      setWriteLoading(false);
    }
  }

  return (
    <section className={styles.widget} aria-labelledby="write-heading">
      <h2 id="write-heading" className={styles.title}>
        Write demo
      </h2>
      <p className={styles.hint}>
        Subject owner may update writable fields; unexpected keys return{" "}
        <strong>403</strong> (mass-assignment guard) and persist nothing.
      </p>
      <div className={styles.buttonRow}>
        <button
          type="button"
          className={styles.button}
          disabled={writeLoading}
          onClick={() => void handleWrite({ given_name: "Demo update" })}
        >
          Write given_name (allowed)
        </button>
        <button
          type="button"
          className={styles.secondaryButton}
          disabled={writeLoading}
          onClick={() => void handleWrite({ is_admin: "true" })}
        >
          Write is_admin (forbidden)
        </button>
      </div>
      {writeError && (
        <p role="alert" className={styles.error}>
          {writeError}
        </p>
      )}
      {writeResult && (
        <pre className={styles.pre}>{JSON.stringify(writeResult, null, 2)}</pre>
      )}
    </section>
  );
}
