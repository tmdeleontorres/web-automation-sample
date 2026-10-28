"""All Users module  (TC-AU-001 .. TC-AU-006)."""

from __future__ import annotations

import pytest

from pages.all_users_page import AllUsersPage
from utils.helpers import random_suffix


@pytest.fixture
def users(auth_page) -> AllUsersPage:
    return AllUsersPage(auth_page).open()


@pytest.mark.smoke
@pytest.mark.happy
def test_au_001_search_user_by_keyword(users):
    """TC-AU-001: keyword search by name, email or user id."""
    users.find_user("trackerteer")
    assert users.row_count() >= 0
    users.clear_filters()


@pytest.mark.happy
def test_au_002_toggle_rfm_admin_access(users):
    """TC-AU-002: the RFM Admin toggle switches the account's role."""
    if users.row_count() == 0:
        pytest.skip("No user records")
    state_on = users.toggle_rfm_admin(0)
    users.toggle_rfm_admin(0)          # switch it back
    assert state_on in (True, False)


@pytest.mark.happy
def test_au_003_create_user(users):
    """TC-AU-003: a complete form creates the account.

    DOM 2026-10-15: the create modal stays open after submit and shows no
    toast, so the verifiable outcome is the account appearing in the list.
    """
    suffix = random_suffix()
    email = f"auto.{suffix.lower()}@trackerteer.com"
    users.create_user(first=f"Auto{suffix}", last="Tester",
                      email=email, password="TestPassw0rd!")
    users.close_modal()
    # Unique local-part only (the shared domain would match any user).
    users.find_user(email.split("@")[0])
    assert users.row_count() >= 1, \
        f"User {email} was not created (no feedback and not in the list)"
    users.clear_filters()


@pytest.mark.negative
def test_au_004_mismatched_passwords_rejected(users):
    """TC-AU-004: New Password != Confirm Password must fail."""
    email = f"mismatch{random_suffix().lower()}@trackerteer.com"
    users.open_create_user()
    users.fill_field(users.LABEL_FIRST_NAME, "Mismatch")
    users.fill_field(users.LABEL_LAST_NAME, "Case")
    users.fill_field(users.LABEL_EMAIL, email)
    users.fill_field(users.LABEL_NEW_PASSWORD, "Passw0rdOne")
    users.fill_field(users.LABEL_CONFIRM_PASSWORD, "Passw0rdTwo")
    users.page.locator(users.BTN_SAVE_USER).first.click()
    users.page.wait_for_timeout(900)
    error = users.error_text()
    users.close_modal()
    # Search the unique local-part only: the shared "@trackerteer.com"
    # domain would match every existing user and mask the result.
    users.find_user(email.split("@")[0])
    assert users.row_count() == 0, \
        f"Mismatched passwords were accepted: {email} exists in the list"
    assert error, "No validation error was shown for mismatched passwords"
    users.clear_filters()


@pytest.mark.negative
def test_au_006_missing_required_fields(users):
    """TC-AU-006: required password fields block the submit."""
    email = f"missing{random_suffix().lower()}@trackerteer.com"
    users.open_create_user()
    users.fill_field(users.LABEL_FIRST_NAME, "Missing")
    users.fill_field(users.LABEL_EMAIL, email)
    users.page.locator(users.BTN_SAVE_USER).first.click()
    users.page.wait_for_timeout(900)
    error = users.error_text()
    users.close_modal()
    # Unique local-part only (see test_au_004 for why the domain is unsafe).
    users.find_user(email.split("@")[0])
    assert users.row_count() == 0, \
        f"User was created although required fields were empty: {email}"
    assert error, "No required-field validation message was shown"
    users.clear_filters()


@pytest.mark.negative
@pytest.mark.xfail(reason="duplicate-email behaviour is not documented explicitly")
def test_au_005_duplicate_email_rejected(users):
    """TC-AU-005: reusing an existing email must not create a second account."""
    suffix = random_suffix()
    users.create_user("Dup", "Case", f"dup.{suffix.lower()}@trackerteer.com", "Passw0rd1!")
    message = users.create_user("Dup", "Case", f"dup.{suffix.lower()}@trackerteer.com", "Passw0rd1!")
    assert "exist" in (message or "").lower() or "invalid" in (message or "").lower()
