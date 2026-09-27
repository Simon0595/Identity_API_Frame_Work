/** Routes: public landing, OAuth callback, protected dashboard. */

import { Route, Routes } from "react-router-dom";
import { AppShell } from "./pages/app/AppShell";
import { Callback } from "./pages/Callback";
import { Landing } from "./pages/Landing";
import { RequireAuth } from "./pages/RequireAuth";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/callback" element={<Callback />} />
      <Route element={<RequireAuth />}>
        <Route path="/app" element={<AppShell />} />
      </Route>
    </Routes>
  );
}
