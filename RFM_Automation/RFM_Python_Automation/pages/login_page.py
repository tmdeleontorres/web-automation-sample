"""LoginPage - authentication flow (TC-AUTH-001 .. TC-AUTH-005)."""

from __future__ import annotations

from config import settings
from pages.base_page import BasePage
from playwright.sync_api import expect


class LoginPage(BasePage):
    path = settings.LOGIN_PATH
    heading = "Welcome Back"

    # --- locators (verified 2026-10-09 against https://dev.master.bwrfm.com/en/login) -- #
    # <input id="rfid-login-username" name="username" placeholder="Enter your email">
    # <input id="rfid-login-password" name="password">
    # <button type="submit" class="btn rfid-login-submit">Sign In</button>
    EMAIL = "#rfid-login-username, input[name=username], input[type=text]"
    PASSWORD = "#rfid-login-password, input[name=password], input[type=password]"
    SUBMIT = "button.rfid-login-submit, button[type=submit]"

    # ------------------------------------------------------------------ #
    def open(self) -> "LoginPage":
        self.page.goto(settings.BASE_URL + self.path, wait_until="domcontentloaded")
        return self

    def email_box(self):
        return self.find(*[self.page.locator(s) for s in self.EMAIL.split(",")],
                         self.page.get_by_label("Email", exact=False),
                         self.page.get_by_placeholder("Email", exact=False))

    def password_box(self):
        return self.find(*[self.page.locator(s) for s in self.PASSWORD.split(",")],
                         self.page.get_by_label("Password", exact=False),
                         self.page.get_by_placeholder("Password", exact=False))

    def submit(self):
        return self.find(*[self.page.locator(s) for s in self.SUBMIT.split(",")],
                         self.page.get_by_role("button", name="Sign in", exact=False),
                         self.page.get_by_role("button", name="Log in", exact=False),
                         self.page.get_by_role("button", name="Login", exact=False))

    # ------------------------------------------------------------------ #
    def login(self, email: str | None = None, password: str | None = None) -> "LoginPage":
        """TC-AUTH-001 - valid credentials land on the Generator page."""
        self.open()
        self.email_box().fill(email or settings.LOGIN_EMAIL)
        self.password_box().fill(password or settings.LOGIN_PASSWORD)
        self.submit().click()
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.page.get_by_text("Encoding Inputs", exact=False).first).to_be_visible()
        return self

    def login_expect_failure(self, email: str, password: str) -> str:
        """Negative login attempts - returns the error text that was shown."""
        self.open()
        self.email_box().fill(email)
        self.password_box().fill(password)
        self.submit().click()
        self.page.wait_for_timeout(1200)
        return self.toast_text()
