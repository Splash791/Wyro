import type { components } from "@wyro/api-types";

export type Trip = components["schemas"]["TripRead"];
export type TripCreate = components["schemas"]["TripCreate"];
export type Day = components["schemas"]["DayRead"];
export type User = components["schemas"]["UserRead"];

const BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN = process.env.EXPO_PUBLIC_DEV_TOKEN ?? "dev-token";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}
