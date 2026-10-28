# The RFM Automation Project — Explained for a Learner

*A guided tour of a real Playwright + pytest test-automation suite, from
"what is automation testing" to "how this suite survives 1.15 million rows."*

---

## 1. The big picture: what problem does this solve?

There is a web app (RFID Master Generator) with **16 modules** — a Generator,
8 list pages, Users, Operators, Import, etc. Before the suite, humans clicked
through **135 test cases** by hand every time the app changed. Now a script
does it in about 6 minutes headless.

Every automation suite is just this loop:

> **Arrange** (get the app into a known state) → **Act** (do what a user would
> do) → **Assert** (check the result is right)

The craft is entirely in two places: **how you organize 135 of those checks so
they do not rot**, and **how you make the browser-waiting reliable**. This
project has good answers to both.

## 2. The stack — three tools, three jobs

| Tool | Job | Why this one |
|---|---|---|
| **Python** | the language | readable, everyone in QA can learn it |
| **Playwright** | drives a real browser (Chromium / Firefox / WebKit) | auto-waits for elements, modern locators |
| **pytest** | runs tests, reports results | fixtures, markers, one command to run everything |

## 3. The folder tour — each folder is one idea

```
RFM_Python_Automation/
├── config/settings.py   <- IDEA: all knobs in one place (URLs, timeouts, credentials)
├── pages/               <- IDEA: Page Object Model — one file per app module
├── tests/               <- IDEA: one test file per module, named after it
├── utils/               <- IDEA: shared helpers + reporting bridge
├── scripts/             <- IDEA: probe scripts — DOM "microscopes" for maintenance
├── fixtures/            <- IDEA: test data files (spreadsheets for import tests)
└── artifacts/           <- IDEA: evidence — screenshots, probe outputs
```

If you can explain why each folder exists, you already understand automation
architecture.

## 4. The Page Object Model — the single most important pattern

**The rule:** tests describe *what the user does*; page objects describe
*where things live on the screen*.

Look at `pages/login_page.py` — the simplest one:

```python
class LoginPage(BasePage):
    path = settings.LOGIN_PATH
    heading = "Welcome Back"

    # locators (verified 2026-10-09 against the live app)
    EMAIL = "#rfid-login-username, input[name=username], input[type=text]"
    PASSWORD = "#rfid-login-password, input[name=password], input[type=password]"
    SUBMIT = "button.rfid-login-submit, button[type=submit]"

    def login(self, email=None, password=None) -> "LoginPage":
        self.open()
        self.email_box().fill(email or settings.LOGIN_EMAIL)
        self.password_box().fill(password or settings.LOGIN_PASSWORD)
        self.submit().click()
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.get_by_text("Encoding Inputs").first).to_be_visible()
        return self
```

Three things to notice as a learner:

1. **Selectors live at the top as constants.** When the app's HTML changes (and
   it *will* — the project README records the app being rebuilt between Oct 9
   and Oct 15), you edit **one line at the top of one file**. No test changes.
2. **The method returns `self`** — so callers can chain:
   `LoginPage(page).login()` reads like a sentence.
3. **`login()` ends with an assertion that you actually landed on the right
   page** ("Encoding Inputs" is the Generator's heading). Page-object methods
   verify their own outcome — failures point at the *step* that broke, not
   mysteriously at the test 50 lines later.

And `base_page.py` is the shared parent — every module page inherits
navigation, `fill_field()`, `find()`, screenshot support. That is
**inheritance used for real DRY**, not homework.

**Why "one file per module"?** 16 modules x their own page object = when the
Style Number List changes, you touch `style_number_list_page.py` and nothing
else. Scales to a team.

## 5. Fixtures (conftest.py) — setup you never repeat

A **fixture** is pytest's word for "code that runs before a test and hands the
test what it needs." The suite has three:

```python
@pytest.fixture
def guest_page(page: Page) -> Page:                       # fresh, NOT logged in
    page.goto(settings.BASE_URL + settings.LOGIN_PATH, ...)
    return page

@pytest.fixture(scope="module")
def auth_page(browser) -> Page:                           # logged in ONCE per file
    context = browser.new_context(viewport=..., locale=..., timezone_id=...)
    page = context.new_page()
    LoginPage(page).login()                               # <- one login serves 8 tests
    yield page
    context.close()
```

**The `scope` concept is the lesson here:**

- Default scope = **function**: fresh browser page per test (isolation, slow).
- `scope="module"` = reuse across every test in one file. That is why the smoke
  run logs in 16 times (once per file) instead of 100+ times.
- `scope="session"` = once for the entire run (fastest, least isolated).

Choosing a scope is a **speed-vs-isolation trade-off** — a real interview
question. This project chose module scope: login once per file, but each file
starts clean.

Also notice the hooks at the top of the same file:

```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    recorder.record(item, report)
```

That is pytest's event system — "after every test, tell the RunRecorder what
happened." This is how the live HTML dashboard gets its data. Hooks let you
observe everything pytest does.

## 6. Anatomy of a real test

From `tests/test_02_generator.py`:

```python
@pytest.fixture
def gen(auth_page) -> GeneratorPage:          # local fixture: builds on auth_page
    page = GeneratorPage(auth_page)
    page.open()
    return page

@pytest.mark.smoke
@pytest.mark.happy
def test_gen_001_generate_single_item_code(gen):
    """TC-GEN-001: one item code -> Generation Summary opens with full details."""
    gen.select_tab(gen.TAB_ITEM_CODE) \
       .enter_item_codes(data.ITEM_CODE_ADDED) \
       .set_starting_serial(data.SERIAL_MIN) \
       .set_quantity(data.QTY_DOCUMENTED) \
       .generate_series()

    assert gen.summary_visible(), "Generation Summary did not open"
    text = gen.summary_text()
    for field in ("Style Number", "Style Name", "Color", "Mother",
                  "Qty", "Serial Range", "EPC Range"):
        assert field.lower() in text.lower(), f"'{field}' missing from summary"
```

Read it aloud — **it is a specification in code**: "select the Item Code tab,
enter codes, set serial and quantity, generate; then the summary must show all
seven fields." Notice:

- **Chainable methods** (line-continuations) — the action section reads like a
  script, not a program.
- **Every assertion has a failure message.** When it breaks at 2 AM, the
  message tells you *what* was missing, not `assert False`.
- **Data comes from `utils/test_data.py`** (`data.QTY_DOCUMENTED`), not
  hardcoded — change test data without touching test code.
- **The docstring carries `TC-GEN-001`** — that is the traceability spine:
  pytest line <-> CSV row <-> HTML dashboard cell.
- **Markers** (`smoke`, `happy`, `boundary`) let you run subsets:
  `pytest -m smoke`, `pytest -m "not slow"`.

## 7. Configuration and secrets (settings.py)

Every tunable lives in one file, and every value can be overridden by an
environment variable:

```python
BASE_URL = os.getenv("RFM_BASE_URL", "https://dev.master.bwrfm.com")
BROWSER  = os.getenv("RFM_BROWSER", "chromium")
HEADLESS = os.getenv("RFM_HEADLESS", "true").lower() in ("1", "true", "yes")
```

**Lesson:** the same code runs on your machine, in CI, or against staging —
you change env vars, never the code. It is also why "watch the run" is just a
flag: headless-vs-headed is a *runtime choice*, not a code change
(`python -m pytest -m smoke --headed --slowmo=250 -v`).

## 8. The hardest skill in automation: synchronization

Browsers are asynchronous. DataTables renders a `Loading RFID records...` row
first, then fills in. If you assert too early, you get a **flaky test** (fails
sometimes, for no reason).

This suite handles sync three ways, in order of preference:

1. **Playwright auto-waiting** — `locator.click()` *already* waits for the
   element to appear, be visible and be enabled. Modern Playwright does most
   of your waiting for you.
2. **Explicit condition waits** — `expect(...).to_be_visible()` polls until
   true or times out.
3. **Custom polling helpers** for the genuinely slow stuff — the star pupil:

```python
# table_search() used to sleep a flat 500 ms. It failed ~30% of the time
# because DataTables filters 1,150,551 client-side rows in ~4 seconds.
# Now it POLLs the row count every 250 ms (up to 15 s) until the count changes.
```

**The rule to memorize:** *never sleep, always poll.* A fixed sleep is either
too short (flaky) or too slow (wasted time). Polling for the actual condition
is both fast and reliable. That one fix is a perfect interview story.

## 9. Resilient locators — how to not break when HTML changes

`base_page.py`'s `find()` shows the cascade strategy:

```python
def find(self, *candidates: Locator) -> Locator:
    """Return the first candidate locator that matches at least one node."""
    for loc in candidates:
        if loc.count() > 0:
            return loc.first
```

And `login_page.py` feeds it fallbacks: exact ID first, then `name=`, then
label, then placeholder. The priority order taught by every Playwright guide:

> **role/name** -> **label** -> **placeholder** -> **CSS id** ->
> **CSS class / XPath** (last resort)

Plus two project-specific refinements worth stealing:

- **Verified CSS constants win.** The login fields *also* carry raw
  `#rfid-login-username` — because a "selector pass" against the live DOM
  proved that ID exists. Fallbacks handle *future* redesigns; the proven
  selector handles *today*.
- **Exact-before-substring matching.** `header_index("RFID")` once matched
  "MOTHER **RFID**" and silently read the wrong column. The fix: exact match
  first, substring only as fallback. Specificity beats cleverness.

## 10. The philosophy: skip != fail, and some tests should be red

Three policies that separate juniors from pros:

- **Skip when data is missing** — a test needing a 5,000-row import fixture
  *skips* (shown as **Blocked** in the sheet) rather than failing. A red test
  should always mean *"something is broken,"* never *"the environment was not
  ready."*
- **xfail for known defects** — "we know this fails, here is the ticket."
- **Intended failures stay red** — `TC-OP-008/009` reproduce a real
  `primedRef is not defined` app bug. The suite **refuses to go green** until
  the app is fixed. Automation that hides bugs is worse than no automation.

## 11. Reporting and traceability — closing the loop

After every test, this hook fires (`conftest.py` -> `RunRecorder`):

```python
STATUS_OF_OUTCOME = {"passed": "Pass", "failed": "Fail", "skipped": "Blocked"}
```

...and rewrites `RFM_Test_Cases_HTML/results.js`. So the HTML sheet — the same
document the manual test cases live in — **updates its Status column live while
tests run**. Parametrized tests sharing one TC-ID keep the *worst* result, so
one red parameter marks the whole case red.

The lesson: **a report nobody reads is a report that does not exist.** Meeting
stakeholders where they already look (the test sheet) is what makes automation
visible — and funded.

## 12. Maintenance: the part nobody writes tutorials about

Apps get rebuilt. This project's answer is the `scripts/` folder — **probe
scripts**: tiny throwaway programs that log in, open one page, and dump the
real DOM to `artifacts/probe_*.txt`:

```powershell
python scripts\inspect_nav.py    # every sidebar module: URL, headings, columns
python scripts\verify_flow.py    # generate -> summary -> save, end to end
```

The workflow: app changed -> run the probe -> read what the DOM *actually*
looks like now -> fix the one constant in the one page object -> re-run. And
the README keeps **evidence tables** ("verified 2026-10-09", "removed
2026-10-15") so the next person starts from facts, not guesses.

This is also where AI fits in the workflow — AI drafts the hypothesis and the
probe; the probe's output decides the fix.

## 13. Follow one click end-to-end (put it all together)

Trace `test_gen_001`:

```
pytest runs test_gen_001(gen)
  |- gen fixture: auth_page (logged-in page) + GeneratorPage wrapper
       |- gen.select_tab("Item Code")
            |- generator_page.py: page.locator(".rfid-gen-mode-btn", has_text=...).click()
                 |- base_page.py: set_default_timeout(15000) already applied
                      |- Playwright: waits for element, scrolls, clicks, auto-recovers
       |- ... fill serial, quantity, click Generate Series
       |- gen.summary_visible() -> #rfid-save-confirm-modal visible?
pytest asserts 7 summary fields -> RunRecorder writes Pass -> results.js updates
```

**Test = the what. Page object = the where. Base page = the how. Playwright =
the hands. Settings = the knobs. RunRecorder = the scoreboard.**

## 14. Practice exercises (in difficulty order)

1. **Run subsets** — `pytest -m smoke -v`, then `pytest -m negative -v`.
   Predict what runs before you press Enter.
2. **Break a locator on purpose** — change `EMAIL` in `login_page.py` to
   `#wrong-id`, run `test_auth_001`, read the failure + screenshot in
   `artifacts/screenshots/`, then fix it.
3. **Write one new test** — add `test_auth_006` (e.g. password field masks
   input) in `test_01_authentication.py` using only existing page-object
   methods.
4. **Write one new page-object method** — add `clear_form()` to
   `generator_page.py`, then use it in a test.
5. **The capstone** — write a probe script modeled on `scripts/inspect_app.py`
   that logs in and dumps the Generator's table headers, then use its output
   to add a column assertion to `test_gen_002`.

---

## Quick command reference

| What you want | Command |
|---|---|
| Run everything | `python -m pytest -v` |
| Watch it run (headed, slowed) | `python -m pytest -m smoke --headed --slowmo=250 -v` |
| One module / one test | `python -m pytest tests/test_02_generator.py -v` / `-k test_gen_001` |
| By marker | `python -m pytest -m smoke` · `-m negative` · `-m boundary` |
| Re-verify selectors | `python scripts\inspect_app.py` · `scripts\verify_flow.py` |

*Source: RFM Automation portfolio walkthrough, October 2026.*
