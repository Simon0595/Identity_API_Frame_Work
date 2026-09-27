/**
 * AppShell tests: role badge and which widgets render.
 *
 * @vitest-environment jsdom
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { NON_OWNER_SUB } from "../../auth/devLogin";
import { clearAccessToken, setAccessToken } from "../../auth/token";
import { AppShell } from "./AppShell";

function mockMeResponse(sub: string, role: string) {
  return vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ sub, role }), { status: 200 }),
  );
}

function renderAppShell() {
  return render(
    <MemoryRouter initialEntries={["/app"]}>
      <Routes>
        <Route path="/app" element={<AppShell />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    setAccessToken("test-jwt");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    clearAccessToken();
  });

  it("renders the role badge from GET /api/v1/me", async () => {
    vi.stubGlobal(
      "fetch",
      mockMeResponse("00000000-0000-4000-8000-000000000001", "admin"),
    );

    renderAppShell();

    await waitFor(() => {
      expect(screen.getByLabelText("Role: admin")).toBeTruthy();
    });
  });

  it("renders AuditWidget for admin and hides WriteWidget", async () => {
    vi.stubGlobal(
      "fetch",
      mockMeResponse("00000000-0000-4000-8000-000000000001", "admin"),
    );

    renderAppShell();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Audit trail" }),
      ).toBeTruthy();
    });
    expect(screen.queryByRole("heading", { name: "Write demo" })).toBeNull();
  });

  it("renders WriteWidget for an owning subject and hides AuditWidget", async () => {
    vi.stubGlobal(
      "fetch",
      mockMeResponse("00000000-0000-4000-8000-000000000001", "subject"),
    );

    renderAppShell();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Write demo" })).toBeTruthy();
    });
    expect(screen.queryByRole("heading", { name: "Audit trail" })).toBeNull();
  });

  it("hides WriteWidget for a non-owner subject", async () => {
    vi.stubGlobal("fetch", mockMeResponse(NON_OWNER_SUB, "subject"));

    renderAppShell();

    await waitFor(() => {
      expect(screen.getByLabelText("Role: subject")).toBeTruthy();
    });
    expect(screen.queryByRole("heading", { name: "Write demo" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Audit trail" })).toBeNull();
  });
});
