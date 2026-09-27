import { ApiError } from "../../api/client";

/** Maps API/client errors to short user-facing strings - widgets share one formatter. */
export function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    return `Request failed (${err.status})`;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Request failed";
}
