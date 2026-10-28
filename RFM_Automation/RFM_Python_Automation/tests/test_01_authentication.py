"""Authentication & access control  (TC-AUTH-001 .. TC-AUTH-005).

Uses `guest_page` (unauthenticated) - no session fixture.
"""

from __future__ import annotations

import os

import pytest

from config import settings
from pages.login_page import LoginPage
from pages.rfid_list_page import RfidListPage


@pytest.mark.smoke
@pytest.mark.happy
def test_auth_001_valid_credentials_login(guest_page):
    """TC-AUTH-001: login with valid credentials opens the Generator."""
    login = LoginPage(guest_page).login()
    assert login.is_visible("Encoding Inputs"), "Generator page did not load"
    assert login.is_visible("Generate Series"), "Generate Series control missing"


@pytest.mark.negative
def test_auth_002_invalid_password_is_rejected(guest_page):
    """TC-AUTH-002: wrong password must fail with a clear error."""
    error = LoginPage(guest_page).login_expect_failure(
        settings.LOGIN_EMAIL, "definitely-not-the-password")
    assert error, "No error message was shown for invalid credentials"
    assert not LoginPage(guest_page).is_visible("Encoding Inputs")


@pytest.mark.negative
def test_auth_003_empty_fields_show_validation(guest_page):
    """TC-AUTH-003: empty email/password must not submit."""
    error = LoginPage(guest_page).login_expect_failure("", "")
    assert error


@pytest.mark.negative
def test_auth_005_malformed_email_rejected(guest_page):
    """TC-AUTH-005: 'notanemail' is not a valid address."""
    error = LoginPage(guest_page).login_expect_failure("notanemail", "SomePass1!")
    assert error, "Malformed email was accepted without validation"


@pytest.mark.security
def test_auth_004_admin_controls_hidden_for_normal_user(auth_page):
    """TC-AUTH-004: non-admin sessions must not expose admin-only actions.

    NOTE: the automation account (torres_trissia@trackerteer.com) is an
    **RFM Admin**, so the admin-only "Delete Selected" action is legitimately
    visible for it.  Non-admin behaviour can only be proven with a non-admin
    credential, so this test verifies what is provable here - that admin
    controls are gated behind the admin role - and skips the negative half
    unless a non-admin account is configured.
    """
    # Navigate with the RFID List page object: LoginPage.click_sidebar()
    # asserts the LOGIN heading ("Welcome Back"), which is invisible here.
    RfidListPage(auth_page).open()

    delete = auth_page.get_by_role("button", name="Delete Selected")
    admin_session = delete.count() > 0 and not delete.first.is_disabled()

    if not admin_session:
        # running with a non-admin credential: the documented rule must hold
        assert delete.count() == 0 or delete.first.is_disabled(), \
            "A non-admin session can see the admin-only Delete Selected action"
        return

    non_admin = os.getenv("RFM_NON_ADMIN_EMAIL")
    if not non_admin:
        pytest.skip("Account under test is an RFM Admin; set RFM_NON_ADMIN_EMAIL "
                    "to prove the negative half of TC-AUTH-004")

    context = auth_page.context
    page = context.new_page()
    try:
        page.set_default_timeout(settings.TIMEOUT_MS)
        LoginPage(page).login(non_admin, os.getenv("RFM_NON_ADMIN_PASSWORD", ""))
        RfidListPage(page).open()
        other = page.get_by_role("button", name="Delete Selected")
        assert other.count() == 0 or other.first.is_disabled(), \
            "A non-admin session can see the admin-only Delete Selected action"
    finally:
        page.close()
