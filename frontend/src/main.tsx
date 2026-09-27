import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { CognitoAuthProvider } from "./auth/CognitoAuthProvider";
import { getAuthMode } from "./config";
import "./styles/theme.css";
import "./index.css";

const app = (
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
);

createRoot(document.getElementById("root")!).render(
  getAuthMode() === "cognito" ? (
    <CognitoAuthProvider>{app}</CognitoAuthProvider>
  ) : (
    app
  ),
);
