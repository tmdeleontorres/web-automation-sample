"""AllUsersPage - "Others > All Users" (accounts, RFM Admin toggle, Create User).

Covers TC-AU-001 .. TC-AU-006.
"""

from __future__ import annotations

from config import settings
from pages.list_page import ListPage


class AllUsersPage(ListPage):
    path = settings.MODULE_PATHS["all_users"]
    sidebar_label = settings.NAV["all_users"]
    heading = "All Users"

    # verified 2026-10-09: user-filter-* ids, rfid-user-table, user-edit-* modal
    FILTER_IDS = {
        "keyword": "#user-filter-keyword",
        "first name": "#user-filter-first-name",
        "last name": "#user-filter-last-name",
        "email": "#user-filter-email",
        "role": "#user-filter-role",
        "status": "#user-filter-status",
    }
    ENTRIES_SELECTOR = "select[name=rfid-user-table_length]"
    TABLE = "#rfid-user-table"

    BTN_CREATE_USER = "Create User"
    BTN_FILTER = "Filter"
    BTN_CLEAR = "Clear Filters"
    BTN_CLEAR_FILTERS = "Clear Filters"
    LABEL_FIRST_NAME = "#user-edit-firstname"
    LABEL_LAST_NAME = "#user-edit-lastname"
    LABEL_EMAIL = "#user-edit-email"
    LABEL_NEW_PASSWORD = "#user-edit-password"
    LABEL_CONFIRM_PASSWORD = "#user-edit-password-confirm"
    LABEL_OPERATOR = "#user-edit-operator"
    # DOM verified 2026-10-15: the modal submit is #user-edit-save-btn
    # (label "Create User" when adding, "Save Changes" when editing).
    BTN_SAVE_USER = "#user-edit-save-btn"
    # The per-row "Access" button opens #user-access-modal, which holds the
    # Admin/User radios (name=user-access-role, values admin|user) and
    # #user-access-save-btn. There is NO inline role toggle in the row.
    ACCESS_MODAL = "#user-access-modal"
    RADIO_ADMIN = "input[name=user-access-role][value=admin]"
    RADIO_USER = "input[name=user-access-role][value=user]"
    BTN_SAVE_ACCESS = "#user-access-save-btn"
    BTN_ACCESS = "button:has-text('Access')"

    # ------------------------------------------------------------------ #
    def find_user(self, keyword: str) -> "AllUsersPage":
        self.page.locator(self.FILTER_IDS["keyword"]).first.fill(keyword)
        self.click_button(self.BTN_FILTER)
        try:
            self.page.wait_for_load_state("networkidle")
        except Exception:
            pass
        self.page.wait_for_timeout(600)
        return self

    def open_access(self, user_row: int = 0) -> "AllUsersPage":
        """Open the row's Access Settings modal (role radios)."""
        self._clear_any_modal()
        self.rows().nth(user_row).locator(self.BTN_ACCESS).first.click()
        self.page.wait_for_timeout(600)
        return self

    def current_role(self) -> str:
        """'admin' or 'user' from the checked radio, else ''."""
        for name, sel in (("admin", self.RADIO_ADMIN),
                          ("user", self.RADIO_USER)):
            loc = self.page.locator(sel)
            if loc.count() and loc.first.is_checked():
                return name
        return ""

    def set_role(self, role: str) -> "AllUsersPage":
        """Check the Admin ('admin') or User ('user') radio and save."""
        self.page.locator(self.RADIO_ADMIN if role == "admin"
                          else self.RADIO_USER).first.check()
        self.page.locator(self.BTN_SAVE_ACCESS).first.click()
        self.page.wait_for_timeout(1200)
        return self

    def toggle_rfm_admin(self, user_row: int = 0) -> bool:
        """Open Access, flip Admin<->User, save, and return the new role.

        Returns True when the account ends up an Admin, False when a User.
        """
        self.open_access(user_row)
        was = self.current_role()
        self.set_role("user" if was == "admin" else "admin")
        return self.current_role() == "admin"

    def open_create_user(self) -> "AllUsersPage":
        self.click_button(self.BTN_CREATE_USER)
        self.page.wait_for_timeout(400)
        return self

    def create_user(self, first: str, last: str, email: str,
                    password: str, confirm: str | None = None) -> str:
        """Fill the #user-edit-* modal fields (verified ids)."""
        self.open_create_user()
        self.page.locator(self.LABEL_FIRST_NAME).first.fill(first)
        self.page.locator(self.LABEL_LAST_NAME).first.fill(last)
        self.page.locator(self.LABEL_EMAIL).first.fill(email)
        self.page.locator(self.LABEL_NEW_PASSWORD).first.fill(password)
        self.page.locator(self.LABEL_CONFIRM_PASSWORD).first.fill(confirm or password)
        # the modal's own submit button (falls back to the page-level Create User)
        save = self.page.locator(self.BTN_SAVE_USER)
        (save.first if save.count()
         else self.page.get_by_role("button", name=self.BTN_CREATE_USER).last).click()
        self.page.wait_for_timeout(1200)
        # The app reports create/save results through the still-open modal
        # (inline error) or a toast/alert once it closes.
        feedback = self.toast_text()
        if feedback:
            return feedback
        modal = self.modal()
        return modal.inner_text().strip() if modal.count() else ""

    def modal_open(self) -> bool:
        modal = self.modal()
        if not modal.count():
            return False
        text = modal.inner_text().lower()
        return "new user" in text or "create user" in text

    def error_text(self) -> str:
        """Visible inline validation message inside the open modal.

        DOM 2026-10-15: rejected submits surface
        `.rfid-gen-status.is-visible.is-error`, e.g. "First name, last name,
        and email are required." (probe J). Empty string when none shows.
        """
        loc = self.page.locator(".rfid-gen-status.is-error:visible")
        return loc.first.inner_text().strip() if loc.count() else ""

    def close_modal(self) -> "AllUsersPage":
        super().close_modal()
        return self
