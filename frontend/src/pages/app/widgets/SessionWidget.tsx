/** Session box: /api/v1/me payload and a logout button. */

import type { MeResponse } from "../../../api/me";
import {
  CognitoLogoutButton,
} from "../../../auth/CognitoLoginPanel";
import { getAuthMode } from "../../../config";
import styles from "./Widget.module.css";

interface SessionWidgetProps {
  me: MeResponse;
  onLogout: () => void;
}

export function SessionWidget({ me, onLogout }: SessionWidgetProps) {
  const authMode = getAuthMode();

  return (
    <section className={styles.widget} aria-labelledby="session-heading">
      <h2 id="session-heading" className={styles.title}>
        Session
      </h2>
      <pre className={styles.pre}>{JSON.stringify(me, null, 2)}</pre>
      {authMode === "cognito" ? (
        <CognitoLogoutButton onLoggedOut={onLogout} />
      ) : (
        <button type="button" className={styles.secondaryButton} onClick={onLogout}>
          Log out
        </button>
      )}
    </section>
  );
}
