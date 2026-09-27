/**
 * Landing page tests. Logged-out view, and redirect when a token is already set.
 *
 * @vitest-environment jsdom
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { clearAccessToken, setAccessToken } from "../auth/token";
import { BRAND_NAME } from "../brand";
import { Landing } from "./Landing";

describe("Landing", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    clearAccessToken();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    clearAccessToken();
  });

  it("renders logged-out with a Sign in CTA and brand hero", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: BRAND_NAME }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { level: 2, name: "Sign in" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Log in as admin" }),
    ).toBeTruthy();
  });

  it("redirects to /app when a bearer token is already in memory", () => {
    setAccessToken("existing-jwt");
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/app" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Dashboard")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
  });
});
