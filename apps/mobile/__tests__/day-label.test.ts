import { formatDayLabel } from "../lib/days";

test("formats a Tokyo day in Tokyo time", () => {
  const label = formatDayLabel({
    date: "2026-04-01",
    city: "Tokyo",
    country_code: "JP",
    time_zone: "Asia/Tokyo",
  });
  expect(label).toContain("Apr 1");
  expect(label).toContain("Tokyo");
});
