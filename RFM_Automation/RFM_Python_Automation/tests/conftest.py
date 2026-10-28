"""Pytest fixtures + hooks.

`page`        - fresh anonymous page (pytest-playwright)
`auth_page`   - page already signed in, scoped per test *module* (fast)
`screenshot`  - on-demand artefact capture

The `pytest_runtest_makereport` hook feeds every result into
`utils.results_report.RunRecorder`, which rewrites
`RFM_Test_Cases_HTML/results.js` after **each** test so the Status column of
the HTML test case updates live while the run is in progress.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from config import settings
from pages.login_page import LoginPage
from utils.results_report import recorder


# --------------------------------------------------------------------------- #
# Live status logging -> HTML test case
# --------------------------------------------------------------------------- #
def pytest_configure(config):
    recorder.start()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    recorder.record(item, report)


def pytest_sessionfinish(session, exitstatus):
    recorder.finish()


# --------------------------------------------------------------------------- #
# Browser fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def base_url() -> str:
    return settings.BASE_URL


@pytest.fixture
def guest_page(page: Page) -> Page:
    """Unauthenticated page pointed at the Generator URL (login tests)."""
    page.goto(settings.BASE_URL + settings.LOGIN_PATH, wait_until="domcontentloaded")
    return page


@pytest.fixture(scope="module")
def auth_page(browser) -> Page:
    """Signed-in page reused by every test inside one test module."""
    context = browser.new_context(
        viewport=settings.VIEWPORT,
        locale=settings.LOCALE,
        timezone_id=settings.TIMEZONE,
    )
    page = context.new_page()
    page.set_default_timeout(settings.TIMEOUT_MS)
    page.set_default_navigation_timeout(settings.NAVIGATION_TIMEOUT_MS)
    LoginPage(page).login()
    yield page
    context.close()


@pytest.fixture
def screenshot(request, page: Page):
    """Capture an artefact on demand:  shot = screenshot('generator_error')."""
    def _take(name: str):
        target = settings.SCREENSHOTS_DIR / f"{name}.png"
        page.screenshot(path=str(target), full_page=True)
        return target
    return _take
