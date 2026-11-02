import { supabase } from "./supabase";
export type Profile = {
  email: string;
  tier: "free" | "plus" | "pro";
  interval: "month" | "year" | null;
  tracking_enabled: boolean;
  onboarding_complete: boolean;
  date_of_birth: string | null;
  discovery_source: string | null;
};
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const base = process.env.EXPO_PUBLIC_API_URL;
  if (!base) throw new Error("Set EXPO_PUBLIC_API_URL to your backend URL.");
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  if (!data.session) throw new Error("Please log in again.");
  const response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${data.session.access_token}`,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const text = await response.text();
  let result;
  try {
    result = text ? JSON.parse(text) : null;
  } catch {
    throw new Error("The server returned an invalid response.");
  }
  if (!response.ok)
    throw new Error(
      typeof result?.detail === "string"
        ? result.detail
        : "Request failed. Please try again.",
    );
  return result as T;
}
const telemetrySession = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
export async function track(
  action: string,
  metadata: Record<string, unknown> = {},
) {
  try {
    await api("/telemetry/action", "POST", {
      action,
      metadata,
      session_id: telemetrySession,
    });
  } catch {
    /* Optional tracking never blocks the app. */
  }
}
