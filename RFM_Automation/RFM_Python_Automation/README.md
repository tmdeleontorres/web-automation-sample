# RFM Automation — Playwright + Python (pytest)

End-to-end test automation for the **RFID Master Generator** web app
<https://dev.master.bwrfm.com/en/rfid_generator/?act=view>

Written for **VS Code** · **Playwright (Python)** · **pytest**, with **one file per
application module** for both page objects and tests.

---

## 1. Setup

```powershell
cd RFM_Python_Automation
python -m pip install -r requirements.txt
python -m playwright install chromium        # browser binaries (once)
```

Open the folder in VS Code and accept the recommended extensions
(Python, Debugpy, Playwright).

## 2. Run

| How | Command |
|---|---|
| Everything | `python -m pytest -v` |
| One module | `python -m pytest tests/test_02_generator.py -v` |
| One test | `python -m pytest tests/test_02_generator.py -k test_gen_001` |
| By marker | `python -m pytest -m smoke` · `-m negative` · `-m boundary` · `-m admin` |
| Watch the browser | `python -m pytest --headed --slowmo=250` |
| VS Code | **Run and Debug** panel → *▶ Run all tests* / *🐞 Debug current test* |

Credentials and environment come from `config/settings.py` and can be overridden:

```powershell
$env:RFM_BASE_URL  = "https://dev.master.bwrfm.com"
$env:RFM_EMAIL     = "you@trackerteer.com"
$env:RFM_PASSWORD  = "..."
$env:RFM_HEADLESS  = "false"
$env:RFM_BROWSER   = "firefox"      # chromium | firefox | webkit
```

---

## 3. Structure — one file per module

```
RFM_Python_Automation/
├── .vscode/                     launch/debug configs, settings, extensions
├── config/
│   └── settings.py              base URL, credentials, timeouts, nav labels, limits
├── pages/                       ← Page Object Model (one file per module)
│   ├── base_page.py             locate / navigate / fill / screenshot helpers
│   ├── list_page.py             shared Filter + table + search + export + modal
│   ├── login_page.py            authentication
│   ├── generator_page.py        Generator (inputs, summary, counters, status)
│   ├── recent_generated_page.py
│   ├── rfid_list_page.py
│   ├── style_number_list_page.py
│   ├── mother_rfid_list_page.py
│   ├── transaction_list_page.py
│   ├── all_users_page.py
│   ├── operator_list_page.py
│   ├── deleted_list_page.py
│   ├── rewrite_rfids_page.py
│   ├── item_code_mismatch_page.py
│   └── rfid_import_page.py
├── tests/                       ← one test file per module
│   ├── conftest.py              guest_page / auth_page (module scope) / screenshot
│   ├── test_01_authentication.py      TC-AUTH-*
│   ├── test_02_generator.py           TC-GEN-*
│   ├── test_03_item_code_status.py    TC-ICS-*
│   ├── test_04_validation_serial_rules.py  TC-EPC-*
│   ├── test_05_save_wms_sync.py       TC-TBL-* / TC-SAVE-* / TC-WMS-* / TC-MCH-*
│   ├── test_06_recent_generated.py    TC-RG-*
│   ├── test_07_rfid_list.py           TC-RL-*
│   ├── test_08_style_number_list.py   TC-SL-*
│   ├── test_09_mother_rfid_list.py    TC-ML-*
│   ├── test_10_transaction_list.py    TC-TL-*
│   ├── test_11_all_users.py           TC-AU-*
│   ├── test_12_operator_list.py       TC-OP-*
│   ├── test_13_deleted_list.py        TC-DL-*
│   ├── test_14_rewrite_rfids.py       TC-RW-*
│   ├── test_15_item_code_mismatch.py  TC-ICM-*
│   └── test_16_rfid_import.py         TC-IMP-*
├── utils/
│   ├── helpers.py               CSV reader, EPC builder, operator-id padding, batches
│   ├── results_report.py        RunRecorder: writes test status into the HTML sheet
│   └── test_data.py             documented item codes, limits, collision examples
├── scripts/                     selector-pass helpers (see section 4)
│   ├── inspect_app.py           login + generator + summary modal DOM dump
│   ├── inspect_nav.py           every sidebar module: URL, headings, columns
│   ├── verify_flow.py           generate -> summary -> save end-to-end walk
│   └── probe_after_save.py      post-save modal / overlay / counters probe
├── fixtures/                    spreadsheets for the import tests (optional)
├── artifacts/                   screenshots + reports (auto-created)
├── pytest.ini                   markers, defaults
├── requirements.txt
└── README.md
```

Test names carry the **TC-\* IDs from the master test case sheet**
(`..\RFM_Test_Cases.csv`, 134 cases), so a report line maps 1:1 to a row of the sheet.

### Markers
`smoke` `happy` `negative` `edge` `boundary` `security` `performance`
`regression` `admin` `slow`

---

## 4. Selector pass — DONE (2026-10-09)

The page objects were first written from the **documentation** alone, then every
locator was replaced with values read from the **live DOM**
(`scripts/inspect_app.py`, `scripts/inspect_nav.py`, `scripts/verify_flow.py`
re-capture them whenever the app changes).

Verified facts the suite depends on:

| Area | Reality |
|---|---|
| Login | `/en/login`, `#rfid-login-username` / `#rfid-login-password`, Sign In |
| Module URLs | every module is a `?act=` on `/en/rfid_generator/` (Import: `/en/rfid_import/`) — see `settings.MODULE_PATHS` |
| Generator inputs | `#rfid-gtin`, `#rfid-serial-start`, `#rfid-quantity`, `#rfid-page-size` |
| Generate flow | Generate Series → `#rfid-save-confirm-modal` ("Generation Summary") → `#rfid-confirm-save` |
| ⚠️ Update flow | **since 2026-10-15 the main `#rfid-generate-series` button morphs** (class `is-update-series`, label "Update Series") while a per-code Qty is pending → same preview modal → `#rfid-confirm-save`. The old `#rfid-current-series-refresh` button is gone (`update_series()` supports both). |
| Save flow | Save → same modal ("Save Summary") → `#rfid-confirm-save` → **`#rfid-post-save-export-modal`** ("Saved Successfully") → `#rfid-close-post-save-export` |
| ⚠️ Screen overlay | after saving, `#rfid-screen-overlay` intercepts every click until the post-save modal is dismissed |
| Counters | `TOTAL GENERATED / STYLES / MOTHER / CHILD` tiles above the series table |
| Copy control | icon-only `button.rfid-row-copy[title="Copy RFID"]` |
| List filters | `#rfid-export-*` (lists), `#rfid-transaction-*`, `#user-filter-*`, `#operator-filter-*` |
| List tables | async: show a `Loading RFID records...` row first → `ListPage.wait_for_table()` |
| Sidebar | `<a>` tags contain icons, so match by `a:has-text(...)` — not by accessible name |

To re-verify after an app update:

```powershell
python scripts\inspect_app.py      # login + generator + summary modal DOM
python scripts\inspect_nav.py      # every sidebar module: URL, headings, columns
python scripts\verify_flow.py      # generate -> summary -> save end to end
```

All three write their findings to `artifacts/inspect_*.txt` / `verify_flow.txt`.

**Nothing in `tests/` hardcodes a selector** — tests only call page-object
methods, so a future app change is fixed by editing the constants at the top of
one page object.

---

## 4b. Re-verification pass (2026-10-15)

The app was rebuilt between 10-09 and 10-15; `scripts/probe_tbl008*.py`
re-verified the Generator flow against the live DOM (`artifacts/probe_tbl008*.txt`):

| Area | Reality (2026-10-15) |
|---|---|
| Update series | old `#rfid-current-series-refresh` **removed** — `#rfid-generate-series` itself morphs to `Update Series` (`.is-update-series`) while any code is pending; preview modal → Continue applies |
| Dirty state | the "Quantity changed" notice area `#rfid-current-series-update` is gone; the per-code badge switches to `is-pending` ("Update", title "Needs update") instead |
| Qty commit | per-code Qty commits **on blur only** (`Tab`); the textarea is rewritten as `code: qty` |
| Bypass syntax | typing `<code>: 5` into the textarea sets that code's Qty to 5 on blur (parses per line) |
| Second generate | generating again **appends** only the new codes' rows (existing rows stay) |
| Remove | the entry stays in the list with class `is-removed`; its textarea line and its rows are dropped |
| RFID cell | `<code>EPC</code><small>NO MOTHER</small>` — read only the `<code>` (`rfid_values()`) |
| Status search | Search item code hides non-matching entries → `item_code_statuses(visible_only=True)` |

**TC-TBL-008** ("Update the quantity of the generated RFID") was added to the
master CSV by the user through the HTML sheet, then synced
(`scripts/sync_html_data.py`, now 135 cases) and automated as
`test_tbl_008_update_item_quantity_updates_series` in
`tests/test_05_save_wms_sync.py` — verified live: 2 rows → 7 rows
(A:2 + B:5 bypass) → Update Series → **10 rows (A:5 + B:5)**.

Case edits made **only in the browser UI** live in `localStorage`
(`rfm_test_cases_v1`), never on disk — read them with:

```powershell
python scripts\read_html_storage.py   # diffs localStorage against data.js
```

---

## 4c. Shared helper rework + module probes (2026-10-15, second pass)

`scripts/probe_mod_a..k.py` (`artifacts/probe_mod_*.txt`) captured the DOM
for every list module; the shared helpers in `pages/list_page.py` and
`pages/base_page.py` were reworked against that evidence:

| Helper | Reality (2026-10-15) |
|---|---|
| `modal()` | every app modal is a `.modal` always in the DOM; the open one has `.in` + is visible. Restricted to `.modal.in/.show:visible` — the Respipe support widget (`[role=dialog]`, "IT Support … Powered by Respipe") has no `.modal` class and was being matched instead of the real dialog |
| `close_modal()` | visible Close button first, then Escape; scrubs a leftover `.modal-backdrop` + `body.modal-open` (the app can leave the overlay mounted, which then blocks every later click) |
| `_clear_any_modal()` | Escape → Close button → force-remove `.in/.show`; needed before opening another modal (Add Operators / Access Settings reused the panel) |
| `rows()` / `header_index()` | scoped to `table:not(.modal table)` — the Add/Edit modals embed their own batch `<table>` whose "Remove"/"CHECK" cells polluted `column_values()` (the "operator RFID reads *Remove*" failure). Also excludes DataTables' **"No matching records found"** row, which is *not* classed `.rfid-gen-empty-row` and used to make a filtered-to-nothing table report `row_count() == 1` |
| `table_search()` | quick-search lives in `div#…_filter` (outside `<table>`) and DataTables listens for **keyup** — `fill()` alone never re-filters |
| `apply_filters()` | `<select>` has no `type` attribute — detected by `tagName`; option matched by label first, then value (e.g. Status `Active` has value `A`; "all" option is labelled **"All Users"** with value `''`) |
| `fill_field` / `select_option` | accept verified CSS constants (`#user-edit-firstname`) in addition to labels; `select_option` prefers `role=combobox` over `get_by_label` (label-matching hit a `<th aria-label>`) |
| `open()` | one `page.goto` retry on timeout (flaky `?act=export` load) |

Module-specific facts confirmed by the probes:

- **Recent Generated** — row action is **View** (`.rfid-view-transact` → `#rfid-transactions-modal`); `#rfid-export-created-by`'s first option is "All Users" (value `''`).
- **Style Number List** — sync counters are `#rfid-style-sync-summary` chips (`Synced 1887` / `Not Synced 1`), not text near the filter.
- **Mother List** — child rows (DATE ADDED (PST)/SOURCE/SERIAL/RFID) only render after expanding a size group via `.rfid-mother-size-toggle` ("View" → "Hide"); header says **(PST)** while values are `PH`.
- **Rewrite RFIDs** — no Before/Current columns: one "RFID REWRITE" cell holds `BEFORE <epc> / CURRENT <epc>` lines; Logs render events as "Rewrite RFID" / "Rewrite RFID Sync" (CSV says `rewrite_rfid*` → `log_actions()` normalises spaces to underscores); "Details" is cell text, not a button.
- **Operator List** — batch rows use `operator-entry-*` classes; CHECK cell is an **account-code gate**: "Waiting for required fields" / "Enter an account code" (`is-pending`) → "Account code is available." (`is-available`); name inputs have **no maxlength** (only the account code is capped at 20).
- **All Users** — no inline role toggle: the row's **Access** button opens `#user-access-modal` with `user-access-role` radios (`admin`/`user`) and `#user-access-save-btn`; create modal submit is `#user-edit-save-btn`; rejected submits show `.rfid-gen-status.is-error` (e.g. "First name, last name, and email are required.") and the modal never closes itself.

**Known defects the suite now documents (intended failures):**

- `TC-GEN-008` — documented generator defect (permanent).
- `TC-OP-008` / `TC-OP-009` — the **Production Lines button is broken**: clicking `#operator-open-production-lines-modal` throws `pageerror: primedRef is not defined`, `#production-lines-modal` never gets `.in`, and no request fires (probe K). The modal cannot open, so the flow cannot run.

---

## 4d. Third pass — full-suite triage + search latency (2026-10-19)

Full suite: **99 passed, 6 failed, 13 skipped, 1 xfailed, 1 xpassed**.
Triage with probes `scripts/probe_mod_{l,m,n}.py` (`artifacts/probe_mod_*.txt`):

| Finding | Evidence | Fix |
|---|---|---|
| `TC-TBL-005` (rg_002b) "search does not filter" was a **timing artifact** | DataTables filtering is asynchronous: measured latency **~1.6 s** (Recent, 2 rows) and **~4.0 s** (RFID List, 1,150,551 client-side rows). Probe L (2 s wait) saw the filter, probe M (1.5 s) did not, and `table_search()` waited only 500 ms | `table_search()` now polls the DataTables info line + row count every 250 ms (up to 15 s) instead of sleeping 500 ms; skips the wait when the input value did not change |
| `TC-RW-003` read the wrong column | `header_index("RFID")` substring-matched **"MOTHER RFID"** (earlier in the header row) and returned the `-` mother column | two-pass match: exact header text first, substring only as fallback |
| `TC-AUTH-004` crashed in `_assert_loaded` | the test navigated with `LoginPage.click_sidebar()`, which asserts the *login* heading ("Welcome Back") after switching pages | navigation via `RfidListPage.open()`; the test now skips (Blocked) without `RFM_NON_ADMIN_*` credentials as designed |
| `TC-AUTH-003` xfail was stale | empty-field validation now shows an error | xfail marker removed (test passes) |
| Style Number List / Transaction List skipped ("No styles/transactions available") | probe N: on 2026-10-19 DataTables never initialises on those pages — no `…_info` line and 0 rows even 10 s after a 60 s `domcontentloaded`; the pages themselves still load | genuine app/data-side state → the skip (→ Blocked) is the correct outcome. New `wait_for_rows()` helper polls up to 8 s before skipping, so a *slow* page no longer causes a false skip; `open()` retry budget raised to 2 × `NAVIGATION_TIMEOUT_MS` (Style page DCL exceeded 15 s on 2026-10-19) |
| RFID List quick-search "never filters" (probe H2/L/M) | premature reads — the filter needs ~4 s over the 1.15 M-row client-side dataset; no ajax fires (search is client-side) | covered by the polling `table_search()` |
| `TC-TBL-005` still read `row_count() == 1` after the filter landed | the DataTables empty-state row is real: `<td colspan=20 class="dataTables_empty">**No RFID records found**</td>` (probe O) — the app *customises* the text, so the old `:has-text('No matching records found')` exclusion never matched | `rows()` now excludes by the standard **`td.dataTables_empty` class** (language-independent; verified in isolation) |
| `TC-RL-007` print toggle passed once then failed ("Yes" != "Yes") | `toggle_print_status()` hard-coded the badge text `"No"`; after one passing run the badge reads `"Yes"`, so the next run clicks nothing | the helper reads the badge's current value, double-right-clicks that text and polls until it flips |
| `TC-SL-004` timed out on a "Hide" button | two causes: (1) size groups render **collapsed** ("View" → "Hide" toggle `button.rfid-mother-size-toggle`, probe P — same widget as the Mother List modal); (2) `collapse_group()` looked the toggle up inside `modal()`, which takes the **last** visible `.modal.in` — when more than one matches, the lookup lands in the wrong dialog and "View"/"Hide" are never found while probe P's global lookup works | `collapse_group()` now finds `.rfid-mother-size-toggle` across ALL open modals, expands first when collapsed, polls for the "Hide" flip and retries once (handlers can bind late on the flaky style page) |
| Style page instability | probe O: 4 navigation attempts, DataTables never initialised; yet during the pytest run minutes later the same page served rows — server-side flakiness | handled by `wait_for_rows()` (skip → Blocked when it truly stays dead) |

Intended permanent failures remain `TC-GEN-008`, `TC-OP-008`, `TC-OP-009`.

---

## 5. Notes

- `auth_page` is **module-scoped**: one login per test file, so a run stays fast.
- Failure screenshots land in `artifacts/screenshots/` (`--screenshot only-on-failure`).
- Tests needing data that does not exist (no rows, no import fixture) **skip**
  instead of failing, so the suite can run against any environment.
- Import tests self-skip until you drop the sample spreadsheets into `fixtures/`
  (see `fixtures/README.txt`).
- Secrets: prefer `$env:RFM_PASSWORD` over editing `settings.py`.
