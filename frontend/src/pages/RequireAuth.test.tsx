/**
 * RequireAuth tests with MemoryRouter. No live backend.
 *
 * @vitest-environment jsdom
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { clearAccessToken, setAccessToken } from "../auth/token";
import { RequireAuth } from "./RequireAuth";

function TestRouter() {
  return (
    <MemoryRouter initialEntries={["/app"]}>
      <Routes>
        <Route path="/" element={<div>Landing page</div>} />
        <Route element={<RequireAuth />}>
          <Route path="/app" element={<div>Dashboard</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("RequireAuth", () => {
  beforeEach(() => {
    clearAccessToken();
  });

  afterEach(() => {
    cleanup();
    clearAccessToken();
  });

  it("redirects an unauthenticated visit to /app back to /", () => {
    render(<TestRouter />);

    expect(screen.getByText("Landing page")).toBeTruthy();
    expect(screen.queryByText("Dashboard")).toBeNull();
  });

  it("renders the protected route when a bearer token is in memory", () => {
    setAccessToken("test-jwt");
    render(<TestRouter />);

    expect(screen.getByText("Dashboard")).toBeTruthy();
    expect(screen.queryByText("Landing page")).toBeNull();
  });
});
