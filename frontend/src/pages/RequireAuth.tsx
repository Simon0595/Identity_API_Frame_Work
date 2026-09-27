/** Route guard. Checks the in-memory token only; a reload means sign in again. */

import { Navigate, Outlet } from "react-router-dom";
import { getAccessToken } from "../auth/token";

export function RequireAuth() {
  if (!getAccessToken()) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
