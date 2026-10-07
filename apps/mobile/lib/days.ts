import type { Day } from "./api";

// Render a trip day's date in that city's IANA time zone.
export function formatDayLabel(day: Day): string {
  const date = new Date(`${day.date}T12:00:00Z`);
  const formatted = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: day.time_zone,
  }).format(date);
  return `${formatted} · ${day.city}`;
}
