/** OAuth return route. After a successful callback we send the user to /app. */

import { Navigate, useNavigate } from "react-router-dom";
import { CognitoLoginPanel } from "../auth/CognitoLoginPanel";
import { clearAccessToken } from "../auth/token";
import { getAuthMode } from "../config";

export function Callback() {
  const navigate = useNavigate();
  const authMode = getAuthMode();

  if (authMode !== "cognito") {
    return <Navigate to="/" replace />;
  }

  return (
    <main>
      <CognitoLoginPanel
        onSession={() => navigate("/app", { replace: true })}
        onError={() => {
          clearAccessToken();
          navigate("/", { replace: true });
        }}
      />
    </main>
  );
}
