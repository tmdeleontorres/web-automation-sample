"""Base Page Object - navigation and low level helpers shared by every module.

SELECTOR NOTE
-------------
The app's DOM was not inspected while these objects were written (no live
browser session), so every locator is expressed with the most resilient
Playwright strategy first (role -> label -> placeholder -> css).  During the
first "selector pass", only the constants at the top of each page object need
to be updated - no test code has to change.
"""

from __future__ import annotations

from config import settings
from playwright.sync_api import Page, Locator, expect


class BasePage:
    """Generic behaviour available on every screen of the RFM app."""

    path: str = "/"                 # relative to settings.BASE_URL
    sidebar_label: str = ""         # label shown in the left sidebar
    heading: str = ""               # main heading of the page

    def __init__(self, page: Page):
        self.page = page
        self.page.set_default_timeout(settings.TIMEOUT_MS)

    # ------------------------------------------------------------------ #
    # Locating
    # ------------------------------------------------------------------ #
    def find(self, *candidates: Locator) -> Locator:
        """Return the first candidate locator that matches at least one node."""
        tried = []
        for loc in candidates:
            try:
                if loc.count() > 0:
                    return loc.first
                tried.append(str(loc))
            except Exception as exc:                      # pragma: no cover - defensive
                tried.append(f"{loc} ({exc})")
        raise AssertionError(f"None of the locators matched: {tried}")

    def by_role(self, role: str, name: str, exact: bool = False) -> Locator:
        return self.page.get_by_role(role, name=name, exact=exact)

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def open(self) -> "BasePage":
        """Open this module's URL directly (one retry for a flaky load)."""
        url = settings.BASE_URL + self.path
        try:
            self.page.goto(url, wait_until="domcontentloaded")
        except Exception:
            # ?act=export pages occasionally exceed the 30 s navigation
            # budget (Style Number List DCL took >15 s on 2026-10-19) - retry
            # with double the NAVIGATION timeout before giving up.
            self.page.goto(url, wait_until="domcontentloaded",
                           timeout=settings.NAVIGATION_TIMEOUT_MS * 2)
        self._assert_loaded()
        return self

    def click_sidebar(self, label: str | None = None) -> "BasePage":
        """Click a left-sidebar entry.

        The sidebar <a> elements contain an <i class="fa ..."> icon, so their
        accessible name does not equal the visible text; matching by text
        inside `a` is the reliable strategy (verified 2026-10-09).
        """
        name = label or self.sidebar_label
        link = self.page.locator("a").filter(has_text=name)
        if not link.count():
            link = self.page.get_by_role("link", name=name, exact=False)

        assert link.count(), f"Sidebar entry '{name}' not found"
        link.first.click()
        try:
            self.page.wait_for_load_state("domcontentloaded")
        except Exception:                       # pragma: no cover - client-side nav
            pass
        self._assert_loaded()
        return self

    def _assert_loaded(self) -> None:
        if self.heading:
            expect(self.page.get_by_text(self.heading, exact=False).first).to_be_visible()

    # ------------------------------------------------------------------ #
    # Fields
    # ------------------------------------------------------------------ #
    def fill_field(self, label: str, value: str, nth: int = 0) -> None:
        """Fill a form control identified by CSS, visible label or placeholder."""
        if self.is_selector(label):                 # verified CSS constant e.g. #user-edit-firstname
            self.page.locator(label).nth(nth).fill(str(value))
            return
        target = self.find(
            self.page.get_by_label(label, exact=False),
            self.page.get_by_placeholder(label, exact=False),
            self.page.get_by_text(label, exact=False),
        )
        boxes = self.page.get_by_label(label, exact=False)
        (boxes.nth(nth) if boxes.count() > nth else target).fill(str(value))

    def select_option(self, label: str, value: str) -> None:
        """Select an option of a <select> found by label (or CSS when `label`
        is a verified selector). Tries label-match first, then value-match."""
        if self.is_selector(label):
            target = self.page.locator(label).first
        else:
            target = self.find(
                self.page.get_by_role("combobox", name=label, exact=False),
                self.page.get_by_label(label, exact=False),
            )
        try:
            target.select_option(label=str(value))
        except Exception:                           # option matched by value
            target.select_option(str(value))

    @staticmethod
    def is_selector(spec: str) -> bool:
        """True when `spec` is a CSS selector rather than a visible name."""
        head = spec.split(" ")[0]
        return (spec[:1] in "#." or ("[" in spec and "]" in spec)
                or head in ("button", "input", "a", "select", "table"))

    def resolve(self, spec: str) -> Locator:
        """A Locator for `spec`, whether it is a verified CSS constant
        (`#rfid-recent-delete`) or a visible control name (`Clear Filters`)."""
        if self.is_selector(spec):
            return self.page.locator(spec).first
        return self.find(
            self.page.get_by_role("button", name=spec, exact=False),
            self.page.get_by_role("link", name=spec, exact=False),
            self.page.get_by_text(spec, exact=False),
        )

    def click_button(self, name: str) -> None:
        """Click a control by CSS constant or by accessible name."""
        self.resolve(name).click()

    def is_visible(self, text: str) -> bool:
        return self.page.get_by_text(text, exact=False).count() > 0

    # ------------------------------------------------------------------ #
    # Feedback / artefacts
    # ------------------------------------------------------------------ #
    def toast_text(self) -> str:
        """Best effort read of the app's flash / toast message.

        The RFM app reports results through Bootstrap modals (e.g.
        #rfid-post-save-export-modal prints "Saved Successfully / 2 saved rows")
        and occasionally through .toast / [role=alert] banners.
        """
        for selector in (".toast", ".alert", "[role=alert]", ".swal2-popup", ".notif",
                         ".modal.show", "#rfid-post-save-export-modal"):
            loc = self.page.locator(selector)
            if loc.count() and loc.first.is_visible():
                return loc.first.inner_text().strip()
        return ""

    def screenshot(self, name: str):
        target = settings.SCREENSHOTS_DIR / f"{name}.png"
        self.page.screenshot(path=str(target), full_page=True)
        return target
