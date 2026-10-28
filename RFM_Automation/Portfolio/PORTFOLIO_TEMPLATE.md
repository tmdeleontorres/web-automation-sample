# Portfolio Template — AI-Assisted Automation Testing

> **How to use this file**
> 1. Copy it into your portfolio repo / Notion / LinkedIn article.
> 2. Replace every `[bracketed placeholder]` with your own details.
> 3. Keep the ✅ **Example** blocks as reference while writing, then delete them.
> 4. Numbers beat adjectives — every claim should be backed by a run, a probe, or a commit.

---

## 1. Headline (30 seconds to hook the reader)

**Template**

```
[Your name] — [Automation QA / SDET] who uses AI to design, build and triage
test automation — without letting AI guess.
[One line: stack] · [One line: domain/scale] · [One line: the outcome you deliver]
```

**✅ Example**

> [Your Name] — Automation QA who uses AI to design, build and triage a
> 135-case Playwright suite — without letting AI guess a single selector.
> Python · Playwright · pytest · Page Object Model · AI-in-the-loop workflow.

---

## 2. About me

**Template**

```
[Role] with [N] years in [domain]. I build end-to-end UI test automation for
[type of product]. My differentiator: a repeatable AI-assisted workflow that
turns requirement documents into a traceable, self-healing-maintenance suite —
where AI drafts and humans verify, never the other way around.
```

**✅ Example**

> Automation QA for a web-based RFID inventory platform. I own the test
> automation suite end to end: 135 test cases across 16 application modules,
> one page object + one test file per module, full 1:1 traceability back to the
> master test-case sheet. AI writes the drafts; live-DOM evidence decides what ships.

---

## 3. My AI-assisted workflow (the core section)

Describe your repeatable process. Use the 6-step loop below as a skeleton and
adapt the tool names to what you actually do.

| Step | Name | What AI does | What the human does |
|---|---|---|---|
| 1 | **Ingest** | Turns requirements / user stories / a CSV sheet into structured test cases with IDs | Reviews coverage, adds domain-only knowledge, assigns traceability IDs |
| 2 | **Design** | Drafts the framework skeleton: folders, config, page objects, fixtures | Owns architecture decisions, naming conventions, secret handling |
| 3 | **Generate** | Writes page-object methods and test code from the drafted cases | Reviews logic, enforces markers (smoke/negative/boundary…), kills over-engineering |
| 4 | **Verify** | Proposes selectors from documentation | **Never trusts them** — every locator is re-read from the live DOM by inspection scripts and only verified constants enter the code |
| 5 | **Triage** | Analyses failures, traces and logs; proposes root-cause hypotheses + probe scripts | Runs the probes, measures, and decides: app bug, flake, or test bug |
| 6 | **Report** | Summarises each run, updates evidence tables and docs | Signs off, files defects, decides what stays red on purpose |

**✅ Example (one line per step, as written in my project docs)**

> Ingest (134 sheet cases → structured suite) → Design (POM, one file per module)
> → Generate (page objects from docs) → Verify (selector pass against live DOM)
> → Triage (measured probes, not opinions) → Report (live results written back
> into the HTML test sheet).

---

## 4. Project spotlight

**Template**

```
### [Project name]
[2–3 sentence summary: what the product is, what you automated, for what audience]

**Stack:** [languages, frameworks, tooling]
**Scope:** [N modules] · [N test cases] · [N environments]
**My role:** [everything you owned]
**AI assist:** [where AI touched the process]
```

**✅ Example**

> ### RFM Automation — RFID Master Generator
> End-to-end test automation for an RFID inventory web app: 16 modules
> (Generator, 8 list modules, Users/Operators, Import, Rewrite, Mismatch…),
> 135 test cases, every test name carrying the TC-ID of the master sheet row
> so a report line maps 1:1 to a spreadsheet line.
>
> **Stack:** Python · Playwright · pytest · pytest-playwright · VS Code
> **Scope:** 16 test modules · 135 TC cases · 11 markers (smoke → slow)
> **Role:** framework, page objects, tests, probes, reporting, defect triage
> **AI assist:** test-case drafting, POM scaffolding, failure-triage hypotheses,
> probe-script drafting, run summaries

---

## 5. Architecture & engineering highlights

Pick 3–5 decisions that show taste, and say *why* they matter.

**Template bullets**

- `[Pattern] — [what it buys you]`
- `[Test policy] — [why]`
- `[Reporting trick] — [outcome]`

**✅ Example**

- **Page Object Model, one file per module** — app change → edit one file's
  constants; *nothing under `tests/` hardcodes a selector*.
- **Skip, don't fail, on missing data** — the suite can run against any
  environment without inventing false failures.
- **Module-scoped auth fixture** — one login per test file keeps full runs fast.
- **RunRecorder bridge** — after *every* test the recorder rewrites
  `results.js` + `test_results.json`, so the HTML test sheet shows live
  Pass / Fail / Blocked status *while the run is still in progress*.
- **Worst-result-wins for parametrised cases** — a single red parameter marks
  the whole TC red.
- **Evidence tables in the README** — every verified DOM fact (selectors,
  flows, gotchas) is written down with the probe that proved it, so the next
  re-verification starts from facts, not memory.

---

## 6. Case studies (the part interviewers remember)

Write 2–4 short stories. Formula: **Symptom → AI hypothesis → Evidence → Fix →
Lesson**.

### Case study A — `[title]`

```
Symptom:  [what failed, how often, when it started]
AI says:  [the plausible hypothesis the model offered]
Evidence: [the probe / measurement you ran — numbers, timestamps, DOM dumps]
Verdict:  [app bug | flake | test bug]
Fix:      [what you changed, in which file]
Lesson:   [the generalizable rule]
```

**✅ Example A — "The four-second search"**

> **Symptom:** quick-search in a list "sometimes doesn't filter" (~30% of runs).
> **AI says:** "the click handler isn't firing — use a `dispatch_event('keyup')`."
> **Evidence:** probes with 2.0 s vs 1.5 s waits gave opposite results; measured
> DataTables client-side filter latency: **~1.6 s** on a 2-row table and
> **~4.0 s** on a **1,150,551-row** table. No ajax — it's all client-side JS.
> **Verdict:** test bug (a fixed 500 ms sleep) against a genuinely slow widget.
> **Fix:** `table_search()` now polls the DataTables info line + row count every
> 250 ms (max 15 s) instead of sleeping.
> **Lesson:** a "flaky" test is usually a *measurement* problem. AI's hypothesis
> was plausible and wrong; the numbers were neither.

**✅ Example B — "The wrong column" (traceability bug)**

> **Symptom:** one rewrite test asserted against a `-` value.
> **AI says:** "the API returned null."
> **Evidence:** `header_index("RFID")` substring-matched **"MOTHER RFID"**, an
> earlier column.
> **Fix:** two-pass header matching — exact text first, substring as fallback —
> plus table scoping that excludes modal tables and the DataTables
> "no records" row (which the app *relabels*, so text-based exclusion failed).
> **Lesson:** assertions are only as good as the locator *before* them.

**✅ Example C — "The AI found a real production bug"**

> **Symptom:** two operator tests could never pass.
> **Evidence:** probe shows clicking the Production Lines button throws
> `pageerror: primedRef is not defined`, the modal never opens, no request fires.
> **Verdict:** real app defect, not a test problem.
> **Action:** tests kept **red on purpose** as documented intended failures —
> automation that "goes green by skipping" is automation that lies.

---

## 7. Metrics & results

**Template**

| Metric | Value | As of |
|---|---|---|
| Test cases automated | [N] | [date] |
| Suite result | [passed / failed / blocked / xfail] | [date] |
| Modules covered | [N / N] | [date] |
| Known defects surfaced | [N] | [date] |
| Traceability | [1:1 TC-ID ↔ sheet row] | [date] |

**✅ Example**

| Metric | Value | As of |
|---|---|---|
| Test cases automated | 135 (from a 134-case sheet + 1 added via automation) | 2026-10-19 |
| Full-suite run | 99 passed · 6 failed (documented defects) · 13 blocked · 1 xfail · 1 xpass | 2026-10-19 |
| Modules covered | 16 / 16 | 2026-10-19 |
| Known defects documented | 3 (TC-GEN-008 permanent; TC-OP-008/009 `primedRef is not defined`) | 2026-10-19 |
| Largest dataset handled | 1,150,551 client-side table rows | 2026-10-19 |
| Traceability | 1:1 — test name ↔ TC-ID ↔ master sheet ↔ HTML dashboard | always |

---

## 8. AI guardrails (the section that earns trust)

**Template**

- AI output is a **draft, not a fact** — every selector and flow is re-verified
  against the live DOM by scripts I run, with the output archived as artifacts.
- **No secrets in prompts** — credentials live in env vars; models see
  redacted config at most.
- **Measurements decide root cause**, never the model's most confident sentence.
- **I own the architecture** — naming, folder layout, markers and the decision
  of what fails vs skips is human.
- **Known-bad stays red** — I never let AI "fix" a failure by weakening the
  assertion.

---

## 9. Toolbelt

**Template**

`[Language]` `[Framework]` `[Runner]` `[Pattern]` `[Reporting]` `[CI]`
`[AI tooling]` `[Version control]` `[Other]`

**✅ Example**

`Python` · `Playwright` · `pytest` · `Page Object Model` · `markers`
· `HTML live test sheet` · `CSV ↔ JS sync scripts` · `DOM probe scripts`
· `env-var config` · `AI pair-programming (draft → verify loop)`

---

## 10. Links & contact

```
Repo:        [url]
Live sheet:  [url or screenshot]
Screenshots: artifacts/screenshots/
Contact:     [email] · [LinkedIn] · [GitHub]
```

---

## Writing tips (delete this block before publishing)

- **Show the loop, not the magic.** Readers trust "AI proposed → I measured →
  here's the artifact" far more than "AI generated tests."
- **Name your failures.** The case studies where AI was *wrong* are the most
  credible content in the portfolio.
- **Refresh the metrics table** after every full run; a stale "as of" date
  quietly discredits the rest.
- **One screenshot of the live dashboard** (the HTML sheet mid-run) is worth a
  thousand words.
