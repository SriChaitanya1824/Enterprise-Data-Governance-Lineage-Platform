import type { Person } from "../types";
const BASE = import.meta.env.VITE_API_URL || "/api";
let accessToken = sessionStorage.getItem("governance_token");
export function setToken(token: string | null) {
  accessToken = token;
  if (token) sessionStorage.setItem("governance_token", token);
  else sessionStorage.removeItem("governance_token");
}
export function hasToken() {
  return !!accessToken;
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      setToken(null);
      window.dispatchEvent(new Event("session-expired"));
    }
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  }
  return data as T;
}
export async function login(email: string, password: string) {
  const result = await api<{ access_token: string; user: Person }>(
    "/auth/login",
    "POST",
    { email, password },
  );
  setToken(result.access_token);
  return result.user;
}
