# Wyro MVP — Open Questions: Recommendations & Decisions

Date: 2026-10-06
Status: Draft for Tyler's review

Working through the six open questions from the MVP spec. Each has a
recommendation; the one that needs your input (the test trip / deadline) is
flagged and asked separately.

---

## 1. Which trip is the real test trip, and when?

**Needs your decision — this sets the build deadline.** Everything else can flex
around school, but the end-to-end test needs a real international trip with
bookings, places to save, and days to plan. Asked separately.

Guidance once you pick a date: work backward. Slice 1 (foundation) is nearly
done. To have the trip test work you need, in order, slices 2 (saved list),
3 (planner+map), 4 (import), 6 (offline), and real auth before you fly. Live
mode (slice 7 / weeks 16-18) is the trimmable one — the trip test still works
without flight alerts.

---

## 2. Pace limit for the plan checker (how many stops/day is "too many")

**Recommendation: default to 5 planned places per day, surfaced as a soft,
editable setting (3–8 range).** The checker flags a day as "overstuffed" when
planned places (not bookings) exceed the limit.

Why 5: solo travel with real transit between stops realistically supports
3–5 substantial places/day before it becomes a forced march. 5 is a forgiving
default that still catches the genuinely overstuffed 8–10-stop days. Because
pace is personal, store it per-trip with a default of 5 so you can tune it on
your real trip and let the acceptance criterion ("catches an overstuffed day")
be met by your own judgment rather than a hardcoded guess.

Refinement for later: weight by estimated dwell time if we ever store it, so a
day of five quick photo-stops isn't flagged like five museums. Out of scope for
the first plan-checker slice — start with a simple count.

---

## 3. Mood chips — is the starting set right?

**Recommendation: keep the five, reorder, and add one.** Starting set was
tired, hungry, outdoors, cheap, rainy-day. Proposed set:

`hungry` · `tired` · `outdoors` · `indoors` · `cheap` · `rainy-day`

- Added **indoors** — it's the natural complement to outdoors and rainy-day and
  the most common "what's open and nearby that isn't weather-dependent" need.
- Dropped nothing; all five original chips map to real ranking signals the
  "what's next?" helper already reads (hours, weather, category, walk time).
- Keep it at ~6 chips max — more becomes a menu, not a quick tap. The helper
  works with zero chips selected too (pure location/time/weather ranking); chips
  are an optional nudge.

Validate on the real trip: log which chips you actually tap (the `pick_log`
table already records `mood`), and prune any that never get used.

---

## 4. Import: forwarding address only, or also share-to-app from day one?

**Recommendation: build both from day one, but the forwarding address is the
primary path and ships first within the import slice.**

- **Forwarding address** (inbound email webhook → LLM extraction) is the
  backbone: it's how airlines/hotels/trains actually reach you (confirmation
  emails), and it works without you doing anything per-booking.
- **Share-to-app** (iOS/Android share sheet → PDF/screenshot → same extraction
  pipeline) is cheap to add *once the extraction pipeline exists*, because it
  reuses the same LLM-to-fixed-schema step and the same review screen. The only
  extra work is registering the share intent and handling file/image input.

So: same slice, forwarding address first (proves the pipeline end to end), then
share-to-app as the second deliverable in that slice. Both feed the Import
Review screen; nothing auto-saves without your confirm.

---

## 5. Which LLM provider for import + mood parsing, and daily spend cap?

**Recommendation: Anthropic Claude, model `claude-haiku-4-5`, called only from
the backend, with a $2/day hard cap.**

Both jobs are a great fit for the cheapest capable Claude tier:

| Job | Model | Why |
|---|---|---|
| Import extraction (email/PDF/screenshot → fixed JSON schema) | `claude-haiku-4-5` | Cheapest tier ($1 / $5 per 1M in/out), has vision (needed for screenshots), and the task is bounded structured extraction. Use **structured outputs** (`output_config: {format: {type: "json_schema", schema: …}}`) so the model is constrained to your booking schema and the output always parses. |
| Mood parsing + one-line pick reasons | `claude-haiku-4-5` | Trivial NL task; Haiku is more than enough and keeps latency low for the one-tap "what's next?". |

Escalation path: if a messy confirmation extracts with low confidence, retry
once on `claude-sonnet-5` ($3/$15, intro $2/$10 through 2026-08-31). Keep Opus
out of the hot path — it's overkill and 5× the cost for bounded extraction.

**Spend cap:** at personal scale this is tiny. A fat day — say 15 imports at
~5K input + 1K output each, plus a dozen mood/pick calls — is well under $0.20
on Haiku. A **$2/day hard cap** (backend counter; stop calling the LLM and show
"import unavailable, try later" past it; alert yourself at $1) is generous
headroom that still protects against a runaway loop or a pasted 500-page PDF.
Also bound per-request input with a token pre-check (reject > ~50K-token inputs)
so one giant attachment can't blow the budget.

Auth/secrets: the Anthropic API key lives only on the backend (never in the
app); the app calls your FastAPI, which calls Claude with a field-masked prompt.

---

## 6. GitHub name — grab "wyro-app"

**Already resolved.** The repo exists at `github.com/Splash791/Wyro` and the
Slice 1 branch is pushed. No separate "wyro-app" grab needed unless you want the
name reserved defensively. Note from the brand section: a crypto wallet also
uses "Wyro", so a future store listing may need "Wyro Travel" — but the GitHub
repo name is fine as-is.

---

## Summary of decisions

| # | Question | Decision |
|---|---|---|
| 1 | Test trip / deadline | **Your call — asked separately** |
| 2 | Pace limit | 5 planned places/day, per-trip editable (3–8) |
| 3 | Mood chips | hungry · tired · outdoors · indoors · cheap · rainy-day |
| 4 | Import surfaces | Both; forwarding address first, share-to-app second, same slice |
| 5 | LLM | Claude `claude-haiku-4-5`, backend-only, structured outputs, $2/day cap, Sonnet 5 escalation |
| 6 | GitHub name | Resolved — `Splash791/Wyro` |
